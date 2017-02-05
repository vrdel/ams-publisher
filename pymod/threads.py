import threading
import os
import sys
import time

class Purger(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        for d in kwargs['kwargs'].iterkeys():
            code = "self.{0} = kwargs['kwargs']['{0}']".format(d)
            exec code
        self.start()

    def run(self):
        i = 0
        while True:
            if self.ev['termth'].is_set():
                self.log.info('Purger: SIGTERM received')
                break
            if i == self.purgeeverysec:
                self.log.info('try purge')
                self.dirq.purge(maxtemp=self.maxtemp, maxlock=self.maxlock)
                i = 0
            time.sleep(self.evsleep)
            i += self.evsleep
