import threading
import os
import sys
import time

from datetime import datetime

class Purger(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.init_attrs(kwargs)
        if not self.daemonized:
            self.daemon = True
        self.start()

    def init_attrs(self, confopts):
        for k in confopts.iterkeys():
            code = "self.{0} = confopts.get('{0}')".format(k)
            exec code

    def run(self):
        wassec = int(datetime.now().strftime('%s'))
        while True:
            if self.ev['termth'].is_set():
                break
            if int(datetime.now().strftime('%s')) - wassec >= self.purgeeverysec:
                self.dirq.purge(maxtemp=self.maxtemp, maxlock=self.maxlock)
                wassec = int(datetime.now().strftime('%s'))
            time.sleep(self.evsleep)
