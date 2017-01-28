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
        self.inmem_q = deque()
        kwargs.update({'inmem_q': self.inmem_q})
        self.publisher = Publish(*args, **kwargs)
        self._run()

    def _cleanup(self):
        raise SystemExit(0)

    def _run(self):
        self.nmsgs_consumed = 0
        self.mq = DQS(path=self.conf['queue'])

        while True:
            if self.ev['term'].isSet():
                self.ev['term'].clear()
                self.cleanup()

            self.consume_dirq(1)
            # publish_msgs(msglist)
            self.publisher.write()
            self.remove_queue_msg()
            time.sleep(0.1)

    def consume_dirq(self, num=0):
        try:
            i = 0
            for name in self.mq:
                if self.mq.lock(name):
                    self.inmem_q.append((name, self.mq.get_message(name)))
                    self.nmsgs_consumed += 1
                    i += 1
                    if num and i == num:
                        break
            else:
                self.log.info('{0} empty'.format(self.mq.path))

        except Exception as e:
            self.log.error(e)

    def remove_queue_msg(self):
        for m in self.inmem_q:
            self.mq.remove(m[0])
        self.inmem_q.clear()


class Publish(Run):
    def __init__(self, *args, **kwargs):
        for d in kwargs.iterkeys():
            code = "self.{0} = kwargs['{0}']".format(d)
            exec code

    def write(self):
        with open('/root/msgs_file', 'a') as fp:
            fp.writelines(['{0}\n'.format(str(m[1])) for m in self.inmem_q])

