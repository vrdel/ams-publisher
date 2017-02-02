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

class Run(object):
    def __init__(self, *args, **kwargs):
        self.log = kwargs['log']
        self.ev = kwargs['ev']
        self.init_confopts(kwargs['conf'])

        self.dirq = DQS(path=self.queue)
        self.inmemq = deque()
        self.pubnumloop = 1 if self.msgbulk > self.queuerate \
                          else self.queuerate / self.msgbulk
        kwargs.update({'inmemq': self.inmemq, 'pubnumloop': self.pubnumloop,
                       'dirq': self.dirq})
        self.publisher = Publish(*args, **kwargs)
        self.purger = Purger(*args, **kwargs)
        self.run()

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
            if self.ev['term'].isSet():
                self.ev['term'].clear()
                self.cleanup()

            if self.consume_dirq_msgs(max(self.msgbulk, self.queuerate)):
                ret, published = self.publisher.write(self.msgbulk)
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


