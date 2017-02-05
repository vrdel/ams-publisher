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
        self.daemon = True
        self.start()

    def run(self):
        while True:
            self.dirq.purge(maxtemp=self.maxtemp, maxlock=self.maxlock)
            time.sleep(self.purgeeverysec)
