import decimal
import os
import sys
import time

from argo_nagios_ams_publisher.publish import FilePublisher
from argo_nagios_ams_publisher.threads import Purger
from collections import deque
from datetime import datetime
from messaging.error import MessageError
from messaging.message import Message
from messaging.queue.dqs import DQS
from multiprocessing import Process

class ConsumerQueue(Process):
    def __init__(self, *args, **kwargs):
        Process.__init__(self, *args, **kwargs)
        self.init_confopts(kwargs['kwargs'])

        self.nmsgs_consumed = 0
        self.sess_consumed = 0

        self.seenmsgs = set()
        self.dirq = DQS(path=self.queue)
        self.inmemq = deque()
        self.pubnumloop = 1 if self.bulk > self.queuerate \
                          else self.queuerate / self.bulk
        kwargs['kwargs'].update({'inmemq': self.inmemq, 'pubnumloop': self.pubnumloop,
                                 'dirq': self.dirq})
        self.publisher = FilePublisher(*args, **kwargs)
        self.purger = Purger(*args, **kwargs)

    def init_confopts(self, confopts):
        for k in confopts.iterkeys():
            code = "self.{0} = confopts.get('{0}')".format(k)
            exec code

    def cleanup(self):
        self.unlock_dirq_msgs(self.seenmsgs)
        raise SystemExit(0)

    def stats(self, reset=False):
        self.log.info('{0} {1}: consumed {2} msgs in {3} hours'.format(self.__class__.__name__,
                                                                       self.name,
                                                                       self.nmsgs_consumed,
                                                                       self.statseveryhour))
        if reset:
            self.nmsgs_consumed = 0
            self.prevstattime = int(datetime.now().strftime('%s'))

    def run(self):
        self.prevstattime = int(datetime.now().strftime('%s'))

        while True:
            try:
                if self.ev['term'].is_set():
                    self.cleanup()

                if self.ev['usr1'].is_set():
                    self.stats()
                    self.publisher.stats()
                    self.ev['usr1'].clear()

                if self.consume_dirq_msgs(max(self.bulk, self.queuerate)):
                    ret, published = self.publisher.write(self.bulk)
                    if ret:
                        self.remove_dirq_msgs()
                    elif published:
                        self.remove_dirq_msgs(published)
                        self.unlock_dirq_msgs(set(e[0] for e in self.inmemq).difference(published))
                    else:
                        self.unlock_dirq_msgs()

                if int(datetime.now().strftime('%s')) - self.prevstattime >= self.statseveryhour * 3600:
                    self.stats(reset=True)
                    self.publisher.stats(reset=True)

                time.sleep(decimal.Decimal(1) / decimal.Decimal(self.queuerate))

            except KeyboardInterrupt:
                self.cleanup()


    def consume_dirq_msgs(self, num=0):
        def _inmemq_append(elem):
            self.inmemq.append(elem)
            self.nmsgs_consumed += 1
            self.sess_consumed += 1
            if num and self.sess_consumed == num:
                self.sess_consumed = 0
                self.seenmsgs.clear()
                return True
        try:
            for name in self.dirq:
                if name in self.seenmsgs:
                    continue
                self.seenmsgs.update([name])
                already_lckd = os.path.exists(self.dirq.get_path(name))
                if not already_lckd and self.dirq.lock(name):
                    if _inmemq_append((name, self.dirq.get_message(name))):
                        return True
                elif already_lckd:
                    if _inmemq_append((name, self.dirq.get_message(name))):
                        return True

        except Exception as e:
            self.log.error(e)

        return False

    def unlock_dirq_msgs(self, msgs=None):
        try:
            msgl = msgs if msgs else self.inmemq
            for m in msgl:
                self.dirq.unlock(m[0] if not isinstance(m, str) else m)
            self.inmemq.clear()
        except (OSError, IOError) as e:
            self.log.error(e)

    def remove_dirq_msgs(self, msgs=None):
        try:
            msgl = msgs if msgs else self.inmemq
            for m in msgl:
                self.dirq.remove(m[0] if not isinstance(m, str) else m)
            self.inmemq.clear()
        except (OSError, IOError) as e:
            self.log.error(e)

def init_dirq_consume(**kwargs):
    log = kwargs['log']
    ev = kwargs['ev']
    evsleep = 2
    consumers = list()

    for k, v in kwargs['conf']['queues'].iteritems():
        kw = dict()

        kw.update({'name': k})
        kw.update({'daemonized': kwargs['daemonized']})
        kw.update({'statseveryhour': kwargs['conf']['general']['statseveryhour']})
        kw.update(kwargs['conf']['queues'][k])
        kw.update(kwargs['conf']['topics'][k])
        kw.update({'log': kwargs['log']})
        kw.update({'ev': kwargs['ev']})
        kw.update({'evsleep': evsleep})

        consumers.append(ConsumerQueue(name=k, kwargs=kw))
        if not kwargs['daemonized']:
            consumers[-1].daemon = True
        consumers[-1].start()

    while True:
        if ev['term'].is_set():
            for c in consumers:
                c.join(1)
            raise SystemExit(0)

        try:
            time.sleep(evsleep)
        except KeyboardInterrupt:
            for c in consumers:
                c.join(1)
            raise SystemExit(0)
