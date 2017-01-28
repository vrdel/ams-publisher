import datetime
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
        self.conf = kwargs['conf']
        self.ev = kwargs['ev']

        self.inmemq = set()
        kwargs.update({'inmem_q': self.inmemq})
        self.publisher = Publish(*args, **kwargs)

        self._run()

    def _cleanup(self):
        raise SystemExit(0)

    def _run(self):
        self.nmsgs_consumed, self.sess_consumed = 0, 0
        self.dirq = DQS(path=self.conf['queue'])

        while True:
            if self.ev['term'].isSet():
                self.ev['term'].clear()
                self.cleanup()

            if self.consume_dirq_msgs(100):
                if self.publisher.write():
                    self.remove_dirq_msgs()
                else:
                    self.unlock_dirq_msgs()

            time.sleep(0.5)

    def consume_dirq_msgs(self, num=0):
        try:
            for name in self.dirq:
                if self.dirq.lock(name):
                    self.inmemq.append((name, self.dirq.get_message(name)))
                    self.nmsgs_consumed += 1
                    self.sess_consumed += 1
                    if num and self.sess_consumed == num:
                       self.sess_consumed = 0
                       return True
            else:
                self.log.info('{0} empty'.format(self.dirq.path))

        except Exception as e:
            self.log.error(e)

        return False

    def unlock_dirq_msgs(self):
        for m in self.inmemq:
            self.dirq.unlock(m[0])
        self.inmemq.clear()

    def remove_dirq_msgs(self):
        for m in self.inmemq:
            self.dirq.remove(m[0])
        self.inmemq.clear()


class Publish(Run):
    def __init__(self, *args, **kwargs):
        for d in kwargs.iterkeys():
            code = "self.{0} = kwargs['{0}']".format(d)
            exec code

    def write(self):
        try:
            with open('/root/msgs_file', 'a') as fp:
                fp.writelines(['{0}\n'.format(str(m[1])) for m in self.inmemq])
                return True

        except Exception as e:
            return False

