import datetime
import decimal
import os
import sys
import time

from collections import deque

from messaging.message import Message
from messaging.error import MessageError
from messaging.queue.dqs import DQS

class Run(object):
    def __init__(self, *args, **kwargs):
        self.log = kwargs['log']
        self.ev = kwargs['ev']
        self.init_confopts(kwargs['conf'])

        self.inmemq = deque()
        kwargs.update({'inmemq': self.inmemq})
        self.publisher = Publish(*args, **kwargs)
        self.run()

    def init_confopts(self, confopts):
        for k in confopts.iterkeys():
            code = "self.{0} = confopts.get('{0}')".format(k)
            exec code

    def cleanup(self):
        raise SystemExit(0)

    def run(self):
        self.nmsgs_consumed, self.sess_consumed = 0, 0
        self.dirq = DQS(path=self.queue)

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
        try:
            for name in self.dirq:
                already_lckd = os.path.exists(self.dirq.get_path(name))
                if not already_lckd and self.dirq.lock(name):
                    _inmemq_append((name, self.dirq.get_message(name)))
                    if num and self.sess_consumed == num:
                        self.sess_consumed = 0
                        return True
                elif already_lckd:
                    _inmemq_append((name, self.dirq.get_message(name)))
                    if num and self.sess_consumed == num:
                        self.sess_consumed = 0
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

class Publish(Run):
    def __init__(self, *args, **kwargs):
        for d in kwargs.iterkeys():
            code = "self.{0} = kwargs['{0}']".format(d)
            exec code
        self.init_confopts(kwargs['conf'])

    def write(self, num=0):
        published = set()
        try:
            for i in range(self.queuerate/self.msgbulk):
                with open('/root/msgs_file', 'a') as fp:
                    fp.writelines(['{0}\n'.format(str(self.inmemq[e][1]))
                                   for e in range(self.msgbulk)])
                published.update([self.inmemq[e][0] for e in range(self.msgbulk)])

                self.inmemq.rotate(-self.msgbulk)

            return True, published

        except Exception as e:
            self.log.error(e)
            return False, published
