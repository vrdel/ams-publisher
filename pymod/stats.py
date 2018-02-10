import socket
import select
import os
import signal

from multiprocessing import Process, Event
from argo_nagios_ams_publisher.shared import Shared


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
                self.shared.log.warning(event)
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
