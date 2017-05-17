import threading
import time
from argo_nagios_ams_publisher.shared import Shared

from datetime import datetime

class Purger(threading.Thread):
    """
       Local cache/directory queue Purger running as separate thread that will
       clean empty intermediate directories, locked and temporary message files
       that exceeded specified threshold.
    """
    def __init__(self, events, worker=None):
        threading.Thread.__init__(self)
        self.shared = Shared(worker=worker)
        self.name = worker
        self.events = events
        self.dirq = self.shared.runtime['dirq']
        if not self.shared.runtime['daemonized']:
            self.daemon = True
        self.start()

    def run(self):
        wassec = int(datetime.now().strftime('%s'))
        while True:
            if self.events['termth-'+self.name].is_set():
                break
            if int(datetime.now().strftime('%s')) - wassec >= self.shared.queue['purgeeverysec']:
                self.dirq.purge(maxtemp=self.shared.queue['maxtemp'], maxlock=self.shared.queue['maxlock'])
                wassec = int(datetime.now().strftime('%s'))
            time.sleep(self.shared.runtime['evsleep'])
