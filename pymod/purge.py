import threading
import time
from argo_nagios_ams_publisher.shared import Shared

from datetime import datetime

class Purger(threading.Thread):
    def __init__(self, log, worker=None):
        threading.Thread.__init__(self)
        self.shared = Shared(worker=worker)
        self.log = log
        self.name = worker
        self.dirq = self.shared.runtime['inmemq']
        if not self.shared.runtime['daemonized']:
            self.daemon = True
        self.start()

    def run(self):
        wassec = int(datetime.now().strftime('%s'))
        while True:
            if self.shared.event('termth').is_set():
                break
            if int(datetime.now().strftime('%s')) - wassec >= self.shared.queue['purgeeverysec']:
                self.dirq.purge(maxtemp=self.shared.queue['maxtemp'], maxlock=self.shared.queue['maxlock'])
                wassec = int(datetime.now().strftime('%s'))
            time.sleep(self.shared.runtime['evsleep'])
