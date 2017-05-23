import decimal
import os
import time

from argo_nagios_ams_publisher.purge import Purger
from argo_nagios_ams_publisher.shared import Shared
from collections import deque
from datetime import datetime
from messaging.queue.dqs import DQS
from multiprocessing import Process, Event

class ConsumerQueue(Process):
    """
       Class represents spawned worker process that will periodically check and
       consume local cache/directory queue. It will initialize associated
       Publisher that will be used to dispatch consumed messages and will also
       spawn a Purger thread that will clean the local cache and keep it with
       the sound data.
    """
    def __init__(self, events, worker=None):
        Process.__init__(self)
        self.shared = Shared(worker=worker)
        self.name = worker
        self.events = events

        self.nmsgs_consumed = 0
        self.sess_consumed = 0

        self.seenmsgs = set()
        self.dirq = DQS(path=self.shared.queue['directory'])
        self.inmemq = deque()
        self.pubnumloop = 1 if self.shared.topic['bulk'] > self.shared.queue['rate'] \
                          else self.shared.queue['rate'] / self.shared.topic['bulk']
        self.shared.runtime.update(inmemq=self.inmemq,
                                   pubnumloop=self.pubnumloop, dirq=self.dirq,
                                   filepublisher=False)
        self.publisher = self.shared.runtime['publisher'](events, worker=worker)
        self.purger = Purger(events, worker=worker)

    def cleanup(self):
        self.unlock_dirq_msgs(self.seenmsgs)

    def stats(self, reset=False):
        def statmsg(hours):
            self.shared.log.info('{0} {1}: consumed {2} msgs in {3:0.2f} hours'.format(self.__class__.__name__,
                                                                        self.name,
                                                                        self.nmsgs_consumed,
                                                                        hours))
        if reset:
            statmsg(self.shared.general['statseveryhour'])
            self.nmsgs_consumed = 0
            self.prevstattime = int(datetime.now().strftime('%s'))
        else:
            sincelaststat = time.time() - self.prevstattime
            statmsg(sincelaststat/3600)

    def run(self):
        self.prevstattime = int(datetime.now().strftime('%s'))
        termev = self.events['term-'+self.name]
        usr1ev = self.events['usr1-'+self.name]
        lck = self.events['lck-'+self.name]
        evgup = self.events['giveup-'+self.name]

        while True:
            try:
                if termev.is_set():
                    self.shared.log.warning('Process {0} received SIGTERM'.format(self.name))
                    lck.acquire(True)
                    self.stats()
                    self.publisher.stats()
                    self.cleanup()
                    lck.release()
                    termev.clear()
                    raise SystemExit(0)

                if usr1ev.is_set():
                    self.shared.log.info('Process {0} received SIGUSR1'.format(self.name))
                    lck.acquire(True)
                    self.stats()
                    self.publisher.stats()
                    lck.release()
                    usr1ev.clear()

                if self.consume_dirq_msgs(max(self.shared.topic['bulk'],
                                              self.shared.queue['rate'])):
                    ret, published = self.publisher.write()
                    if ret:
                        self.remove_dirq_msgs()
                    elif published:
                        self.shared.log.error('{0} {1} giving up'.format(self.__class__.__name__, self.name))
                        self.stats()
                        self.publisher.stats()
                        self.remove_dirq_msgs(published)
                        self.unlock_dirq_msgs(set(e[0] for e in self.inmemq).difference(published))
                        evgup.set()
                        raise SystemExit(0)
                    else:
                        self.shared.log.error('{0} {1} giving up'.format(self.__class__.__name__, self.name))
                        self.stats()
                        self.publisher.stats()
                        self.unlock_dirq_msgs()
                        evgup.set()
                        raise SystemExit(0)

                if int(datetime.now().strftime('%s')) - self.prevstattime >= self.shared.general['statseveryhour'] * 3600:
                    self.stats(reset=True)
                    self.publisher.stats(reset=True)

                time.sleep(decimal.Decimal(1) / decimal.Decimal(self.shared.queue['rate']))

            except KeyboardInterrupt:
                self.cleanup()
                raise SystemExit(0)

    def consume_dirq_msgs(self, num=0):
        def _inmemq_append(elem):
            self.inmemq.append(elem)
            self.nmsgs_consumed += 1
            self.sess_consumed += 1
            if num and self.sess_consumed == num:
                self.sess_consumed = 0
                self.seenmsgs.clear()
                return True
        try:
            for name in self.dirq:
                if os.stat(self.shared.queue['directory'] + name).st_size < 8:
                    os.unlink(self.shared.queue['directory'] + name)
                if name in self.seenmsgs:
                    continue
                self.seenmsgs.update([name])
                already_lckd = os.path.exists(self.dirq.get_path(name))
                if not already_lckd and self.dirq.lock(name):
                    if _inmemq_append((name, self.dirq.get_message(name))):
                        return True
                elif already_lckd:
                    if _inmemq_append((name, self.dirq.get_message(name))):
                        return True

        except Exception as e:
            self.shared.log.error(e)

        return False

    def unlock_dirq_msgs(self, msgs=None):
        try:
            msgl = msgs if msgs else self.inmemq
            for m in msgl:
                self.dirq.unlock(m[0] if not isinstance(m, str) else m)
            self.inmemq.clear()
        except (OSError, IOError) as e:
            self.shared.log.error(e)

    def remove_dirq_msgs(self, msgs=None):
        try:
            msgl = msgs if msgs else self.inmemq
            for m in msgl:
                self.dirq.remove(m[0] if not isinstance(m, str) else m)
            self.inmemq.clear()
        except (OSError, IOError) as e:
            self.shared.log.error(e)

