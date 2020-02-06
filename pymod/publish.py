import time
import json

from avro.io import BinaryEncoder
from avro.io import DatumWriter
from io import BytesIO

from argo_ams_library.ams import ArgoMessagingService
from argo_ams_library.amsmsg import AmsMessage
from argo_nagios_ams_publisher.shared import Shared
from argo_nagios_ams_publisher.stats import StatSig
from argo_ams_library.amsexceptions import AmsConnectionException, AmsServiceException


class Publish(StatSig):
    """
       Base publisher class that initialize statistic data
    """
    def __init__(self, worker=None):
        super(Publish, self).__init__(worker=worker)

    def write(self, num=0):
        pass

    def _increm_intervalcounters(self, num):
        now = int(time.time())
        counter = self.shared.statint[self.name]['published']
        counter[now] = num + counter.get(now, 0)
        self.shared.statint[self.name]['published_periodic'] += num


class FilePublisher(Publish):
    """
       Publisher that write the messages into a file. Used only for debugging
       purposes.
    """
    def __init__(self, events, worker=None):
        self.shared = Shared(worker=worker)
        self.inmemq = self.shared.runtime['inmemq']
        self.pubnumloop = self.shared.runtime['pubnumloop']
        self.name = worker
        super(FilePublisher, self).__init__(worker=worker)

    def write(self, num=0):
        published = set()
        try:
            for i in range(self.pubnumloop):
                with open('/{0}/{1}'.format(self.shared.general['publishmsgfiledir'], self.shared.topic['topic']), 'a') as fp:
                    fp.writelines(['{0}\n'.format(str(self.inmemq[e][1]))
                                   for e in range(self.shared.topic['bulk'])])
                published.update([self.inmemq[e][0] for e in range(self.shared.topic['bulk'])])
                self.shared.stats['published'] += self.shared.topic['bulk']

                self.inmemq.rotate(-self.shared.topic['bulk'])

            return True, published

        except Exception as e:
            self.shared.log.error(e)
            return False, published


class MessagingPublisher(Publish):
    """
       MessagingPublisher class that dispatch messages to ARGO Messaging
       service.
    """
    def __init__(self, events, worker=None):
        self.shared = Shared(worker=worker)
        self.inmemq = self.shared.runtime['inmemq']
        self.pubnumloop = self.shared.runtime['pubnumloop']
        super(MessagingPublisher, self).__init__(worker=worker)
        self.ams = ArgoMessagingService(endpoint=self.shared.topic['host'],
                                        token=self.shared.topic['key'],
                                        project=self.shared.topic['project'])
        self.name = worker
        self.events = events

    def construct_msg(self, msg):
        def _part_date(timestamp):
            import datetime

            date_fmt = '%Y-%m-%dT%H:%M:%SZ'
            part_date_fmt = '%Y-%m-%d'
            if timestamp:
                d = datetime.datetime.strptime(timestamp, date_fmt)
            else:
                d = datetime.datetime.now()

            return d.strftime(part_date_fmt)

        def _avro_serialize(msg):
            avro_writer = DatumWriter(self.shared.topic['schema'])
            bytesio = BytesIO()
            encoder = BinaryEncoder(bytesio)
            avro_writer.write(msg, encoder)

            return bytesio.getvalue()

        plainmsg = dict()
        plainmsg.update(msg.header)
        plainmsg.update(self.body2dict(msg.body))
        plainmsg.update(tags=self.tag2dict(msg.body))
        timestamp = plainmsg.get('timestamp', None)

        m = None
        if self.shared.topic['avro']:
            m = _avro_serialize(plainmsg)
        else:
            m = json.dumps(plainmsg)

        return _part_date(timestamp), m

    def _extract_body(self, body, fields, maps=None):
        msg = dict()

        bodylines = body.split('\n')
        for line in bodylines:
            split = line.split(': ', 1)
            if len(split) > 1:
                key = split[0]
                value = split[1]

                if key not in set(fields):
                    continue

                if maps and key in maps:
                    key = maps[key]

                msg[key] = value

        return msg

    def body2dict(self, body):
        if self.shared.topic['msgtype'] == 'alarm':
            body_fields = ['details', 'vo', 'site', 'roc', 'urlhistory', 'urlhelp']
        elif self.shared.topic['msgtype'] == 'metric_data':
            body_fields = ['summary', 'message', 'actual_data']

        return self._extract_body(body, body_fields)

    def tag2dict(self, body):
        if self.shared.topic['msgtype'] == 'metric_data':
            tag_fields = ['vofqan', 'voname', 'roc', 'site']
        elif self.shared.topic['msgtype'] == 'alarm':
            tag_fields = []

        body_to_tagname = dict(site='endpoint_group')

        return self._extract_body(body, tag_fields, body_to_tagname)

    def _write(self, msgs):
        t = 1
        lck = self.events['lck-'+self.name]
        published = set()
        for i in range(self.pubnumloop):
            try:
                while t <= self.shared.topic['retry']:
                    try:
                        lck.acquire(False)
                        self.ams.publish(self.shared.topic['topic'], msgs, timeout=self.shared.topic['timeout'])
                        published.update([self.inmemq[e][0] for e in range(self.shared.topic['bulk'])])
                        self._increm_intervalcounters(self.shared.topic['bulk'])
                        self.inmemq.rotate(-self.shared.topic['bulk'])
                        break

                    except (AmsServiceException, AmsConnectionException)  as e:
                        self.shared.log.warning('{0} {1}: {2}'.format(self.__class__.__name__, self.name, e))

                        if t == self.shared.topic['retry']:
                            raise e
                        else:
                            s = self.shared.topic['sleepretry']
                            n = s/self.shared.runtime['evsleep']
                            i = 0
                            while i < n:
                                if self.events['term-'+self.name].is_set():
                                    self.shared.log.info('Process {0} received SIGTERM'.format(self.name))
                                    raise e
                                if self.events['usr1-'+self.name].is_set():
                                    self.stats()
                                    self.events['usr1-'+self.name].clear()
                                time.sleep(self.shared.runtime['evsleep'])
                                i += 1
                            else:
                                self.shared.log.warning('{0} {1} Giving try: {2} after {3} seconds'.
                                                        format(self.__class__.__name__, self.name, t, s))
                                pass

                    # catch errors not handled in ams-library, report them in
                    # logs and retry
                    except Exception as e:
                        self.shared.log.error('{0} {1}: {2}'.format(self.__class__.__name__, self.name, e))
                        time.sleep(self.shared.runtime['evsleep'])
                        self.shared.log.error('Unexpected error, retry after {0} seconds'.
                                              format(self.shared.runtime['evsleep']))
                        pass

                    finally:
                        lck.release()

                    t += 1

            except (AmsServiceException, AmsConnectionException) as e:
                return False, published

        return True, published

    def write(self):
        msgs = [self.construct_msg(self.inmemq[e][1]) for e in range(self.shared.topic['bulk'])]
        msgs = map(lambda m: AmsMessage(attributes={'partition_date': m[0],
                                                    'type': self.shared.topic['msgtype']},
                                        data=m[1]), msgs)
        return self._write(msgs)
