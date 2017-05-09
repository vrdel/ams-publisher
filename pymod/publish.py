import avro.schema
import time
import json

from avro.io import BinaryEncoder
from avro.io import DatumReader
from avro.io import DatumWriter
from base64 import b64encode
from collections import deque
from io import BytesIO

from argo_ams_library.ams import ArgoMessagingService
from argo_ams_library.amsmsg import AmsMessage
from argo_nagios_ams_publisher.shared import Shared
from argo_ams_library.amsexceptions import AmsConnectionException, AmsServiceException

class Publish(object):
    def __init__(self, worker=None):
        self.shared = Shared(worker=worker)
        self.nmsgs_published = 0
        self.laststattime = time.time()
        self.name = worker

    def init_attrs(self, confopts):
        for k in confopts.iterkeys():
            code = "self.{0} = confopts.get('{0}')".format(k)
            exec code

    def stats(self, reset=False):
        def statmsg(hours):
            self.shared.log.info('{0} {1}: sent {2} msgs in {3:0.2f} hours'.format(self.__class__.__name__,
                                                                                   self.name,
                                                                                   self.nmsgs_published,
                                                                                   hours
                                                                                  ))
        if reset:
            statmsg(self.shared.general['statseveryhour'])
            self.nmsgs_published = 0
            self.laststattime = time.time()
        else:
            sincelaststat = time.time() - self.laststattime
            statmsg(sincelaststat/3600)

    def write(self, num=0):
        pass

class FilePublisher(Publish):
    def __init__(self, worker=None):
        self.shared = Shared(worker=worker)
        self.inmemq = self.shared.runtime['inmemq']
        self.pubnumloop = self.shared.runtime['pubnumloop']
        self.worker = worker
        super(FilePublisher, self).__init__(worker=worker)

    def write(self, num=0):
        published = set()
        try:
            for i in range(self.pubnumloop):
                with open('/{0}/{1}'.format(self.publishmsgfiledir, self.topic), 'a') as fp:
                    fp.writelines(['{0}\n'.format(str(self.inmemq[e][1]))
                                   for e in range(self.bulk)])
                published.update([self.inmemq[e][0] for e in range(self.bulk)])
                self.nmsgs_published += self.bulk

                self.inmemq.rotate(-self.bulk)

            return True, published

        except Exception as e:
            self.shared.log.error(e)
            return False, published

class MessagingPublisher(Publish):
    def __init__(self, events, worker=None):
        self.shared = Shared(worker=worker)
        self.inmemq = self.shared.runtime['inmemq']
        self.pubnumloop = self.shared.runtime['pubnumloop']
        self.schema = self.shared.runtime['schema']
        super(MessagingPublisher, self).__init__(worker=worker)
        self.ams = ArgoMessagingService(endpoint=self.shared.topic['host'],
                                        token=self.shared.topic['key'],
                                        project=self.shared.topic['project'])
        self.name = worker
        self.events = events

    def body2dict(self, body):
        d = dict()
        bodylines = body.split('\n')
        for line in bodylines:
            split = line.split(': ', 1)
            if len(split) > 1:
                key = split[0]
                value = split[1]
                d[key] = value.decode('utf-8', 'replace')

        return d

    def construct_metricmsg(self, msg):
        def _part_date(timestamp):
            import datetime

            date_fmt = '%Y-%m-%dT%H:%M:%SZ'
            part_date_fmt = '%Y-%m-%d'
            d = datetime.datetime.strptime(timestamp, date_fmt)

            return d.strftime(part_date_fmt)

        def _avro_serialize(msg):
            avro_writer = DatumWriter(self.schema)
            bytesio = BytesIO()
            encoder = BinaryEncoder(bytesio)
            avro_writer.write(msg, encoder)

            return bytesio.getvalue()

        plainmsg = dict()
        plainmsg.update(msg.header)
        plainmsg.update(self.body2dict(msg.body))

        return _part_date(plainmsg['timestamp']), _avro_serialize(plainmsg)

    def construct_alarmsg(self, msg):
        d = self.body2dict(msg.body)
        d.update(msg.header)

        return json.dumps(d)

    def write(self, num=0):
        t = 1
        lck = self.events['lck-'+self.name]
        for i in range(self.pubnumloop):
            msgs = list()
            if self.shared.topic['type'] == 'metric':
                msgs = [self.construct_metricmsg(self.inmemq[e][1]) for e in range(self.shared.topic['bulk'])]
                msgs = map(lambda m: AmsMessage(attributes={'partition_date': m[0],
                                                            'type': 'metric_data'},
                                                data=m[1]).dict(), msgs)
            elif self.shared.topic['type'] == 'alarm':
                msgs = [self.construct_alarmsg(self.inmemq[e][1]) for e in range(self.shared.topic['bulk'])]
                msgs = map(lambda m: AmsMessage(attributes={'type': 'alarm'},
                                                data=m).dict(), msgs)
            try:
                while t <= self.shared.general['publishretry']:
                    try:
                        lck.acquire(False)
                        published = set()
                        self.ams.publish(self.shared.topic['topic'], msgs, timeout=self.shared.general['publishtimeout'])
                        published.update([self.inmemq[e][0] for e in range(self.shared.topic['bulk'])])
                        self.nmsgs_published +=  self.shared.topic['bulk']
                        self.inmemq.rotate(-self.shared.topic['bulk'])

                        return True, published

                    except (AmsServiceException, AmsConnectionException)  as e:
                        self.shared.log.warning('{0} {1}: {2}'.format(self.__class__.__name__, self.name, e))

                        if t == self.shared.general['publishretry']:
                            raise e
                        else:
                            # add some exponential jitter slowdown here
                            s = 30
                            time.sleep(s)
                            self.shared.log.warning('{0} {1} Giving try: {2} after {3} seconds'.format(self.__class__.__name__, self.name, t, s))
                            pass

                    finally:
                        lck.release()

                    t += 1

            except (AmsServiceException, AmsConnectionException) as e:
                return False, published
