import threading
import os
import sys
import time

from datetime import datetime

class Purger(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        for d in kwargs['kwargs'].iterkeys():
            code = "self.{0} = kwargs['kwargs']['{0}']".format(d)
            exec code
        self.start()

    def run(self):
        wassec = int(datetime.now().strftime('%s'))
        while True:
            if self.ev['termth'].is_set() or self.ev['intth'].is_set():
                break
            if int(datetime.now().strftime('%s')) - wassec >= self.purgeeverysec:
                self.dirq.purge(maxtemp=self.maxtemp, maxlock=self.maxlock)
                wassec = int(datetime.now().strftime('%s'))
            time.sleep(self.evsleep)
