import socket
import select
import os
import signal
import time

from multiprocessing import Process, Event
from argo_nagios_ams_publisher.shared import Shared

class StatSig(object):
    def __init__(self, worker):
        self.laststattime = time.time()
        self.nmsgs_published = 0
        self.name = worker
        if 'Publish' in self.__class__.__name__:
            self.msgdo = 'sent'
        elif 'Consume' in self.__class__.__name__:
            self.msgdo = 'consumed'

    def stats(self, reset=False):
        def statmsg(hours):
            self.shared.log.info('{0} {1}: {2} {3} msgs in {4:0.2f} hours'.format(self.__class__.__name__,
                                                                                  self.name,
                                                                                  self.msgdo,
                                                                                  self.nmsgs_published,
                                                                                  hours
                                                                                  ))
        if reset:
            statmsg(self.shared.general['statseveryhour'])
            self.nmsgs_published = 0
            self.laststattime = time.time()
        else:
            sincelaststat = time.time() - self.laststattime
            statmsg(sincelaststat/3600)

class Stats(Process):
    def __init__(self, events, sock):
        Process.__init__(self)
        self.events = events
        self.shared = Shared()
        self.sock = sock

        try:
            self.sock.listen(1)
        except socket.error as m:
            self.shared.log.error('Cannot initialize Stats socket %s - %s' % (sockpath, repr(m)))
            raise SystemExit(1)

    def _cleanup(self):
        self.sock.close()
        os.unlink(self.shared.general['statsocket'])
        raise SystemExit(0)

    def run(self):
        self.poller = select.poll()
        self.poller.register(self.sock.fileno(), select.POLLIN)

        while True:
            try:
                event = self.poller.poll(float(self.shared.runtime['evsleep'] * 1000))
                if len(event) > 0 and event[0][1] & select.POLLIN:
                    conn, addr = self.sock.accept()
                    data = conn.recv(32)
                    self.shared.log.info('Received query %s' % data)

                if self.events['term-stats'].is_set():
                    self.shared.log.info('Stats received SIGTERM')
                    self.events['term-stats'].clear()
                    self._cleanup()

            except KeyboardInterrupt:
                self._cleanup()
