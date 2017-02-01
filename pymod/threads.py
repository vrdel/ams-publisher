import threading
import os
import sys
import time

class Purger(threading.Thread):
    def __init__(self, *args, **kwargs):
        for d in kwargs.iterkeys():
            code = "self.{0} = kwargs['{0}']".format(d)
            exec code
        self.init_confopts(kwargs['conf'])
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()

    def init_confopts(self, confopts):
        for k in confopts.iterkeys():
            code = "self.{0} = confopts.get('{0}')".format(k)
            exec code

    def run(self):
        while True:
            self.dirq.purge(maxtemp=self.maxtemp, maxlock=self.maxlock)
            time.sleep(self.purgeeverysec)
