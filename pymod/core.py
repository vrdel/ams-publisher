import datetime
import os
import sys
import time

from messaging.message import Message
from messaging.error import MessageError
from messaging.queue.dqs import DQS

class Run(object):
    def __init__(self, *args, **kwargs):
        self.log = kwargs['log']
        self.conf = kwargs['conf']
        self.thev = kwargs['ev']
        self._run()

    def _cleanup(self):
        raise SystemExit(0)

    def _run(self):
        self.msgl = list()
        self.nmsgs_consumed = 0
        mq = DQS(path=self.conf['queue'])

        while True:
            if self.thev['term'].isSet():
                self.thev['term'].clear()
                self.cleanup()

            self.consume_queue(mq)
            # publish_msgs(msglist)
            time.sleep(1)

    def consume_queue(self, mq, num=0):
        try:
            for name in mq:
                if mq.lock(name):
                    self.msgl.append(mq.get_message(name))
                    mq.remove(name)
                    if num and i == num:
                        break
                    self.nmsgs_consumed += 1
            else:
                self.log.info('{0} empty'.format(mq.path))

        except Exception as e:
            self.log.error(e)

    def publish_msgs(self, msglist):
        pass

