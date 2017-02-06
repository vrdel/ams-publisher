import datetime
import decimal
import os
import sys
import time

from argo_nagios_ams_publisher.threads import Purger
from argo_nagios_ams_publisher.publish import Publish
from collections import deque
from messaging.error import MessageError
from messaging.message import Message
from messaging.queue.dqs import DQS
from multiprocessing import Process

class ConsumerDirQ(Process):
    def __init__(self, *args, **kwargs):
        Process.__init__(self, *args, **kwargs)
        self.init_confopts(kwargs['kwargs'])

        self.dirq = DQS(path=self.queue)
        self.inmemq = deque()
        self.pubnumloop = 1 if self.bulk > self.queuerate \
                          else self.queuerate / self.bulk
        kwargs['kwargs'].update({'inmemq': self.inmemq, 'pubnumloop': self.pubnumloop,
                                 'dirq': self.dirq})
        self.publisher = Publish(*args, **kwargs)
        self.purger = Purger(*args, **kwargs)

    def init_confopts(self, confopts):
        for k in confopts.iterkeys():
            code = "self.{0} = confopts.get('{0}')".format(k)
            exec code

    def cleanup(self):
        raise SystemExit(0)

    def run(self):
        self.nmsgs_consumed, self.sess_consumed = 0, 0
        self.seenmsgs = set()

        while True:
            if self.ev['term'].is_set():
                self.cleanup()

            if self.consume_dirq_msgs(max(self.bulk, self.queuerate)):
                ret, published = self.publisher.write(self.bulk)
                if ret:
                    self.remove_dirq_msgs()
                elif published:
                    self.remove_dirq_msgs(published)
                    self.unlock_dirq_msgs(set(e[0] for e in self.inmemq).difference(published))
                else:
                    self.unlock_dirq_msgs()

            time.sleep(decimal.Decimal(1) / decimal.Decimal(self.queuerate))

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
                self.dirq.unlock(m[0])
            self.inmemq.clear()
        except (OSError, IOError) as e:
            self.log.error(e)

    def remove_dirq_msgs(self, msgs=None):
        try:
            msgl = msgs if msgs else self.inmemq
            for m in msgl:
                self.dirq.remove(m[0])
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
        kw.update(kwargs['conf']['queues'][k])
        kw.update(kwargs['conf']['topics'][k])
        kw.update({'log': kwargs['log']})
        kw.update({'ev': kwargs['ev']})
        kw.update({'evsleep': evsleep})

        consumers.append(ConsumerDirQ(name=k, kwargs=kw))
        consumers[-1].start()

    while True:
        if ev['term'].is_set():
            for c in consumers:
                c.join(1)
            raise SystemExit(0)

        time.sleep(evsleep)
