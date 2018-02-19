import socket
import select
import os
import time
import re
import copy

from threading import Thread
from multiprocessing import Process
from argo_nagios_ams_publisher.shared import Shared

maxcmdlength = 128

class StatSig(object):
    """
       Class is meant to be subclassed by ConsumerQueue and Publish classes for
       the purpose of implementing common methods that will be called on SIGUSR1
       event and write consumed/published statistics for each worker.
    """
    def __init__(self, worker):
        self.laststattime = time.time()
        self.name = worker
        self.msgdo = 'sent' if self._iam_publisher() else 'consumed'
        self._reset()

    def _stat_msg(self, hours):
        nmsg = self.shared.stats['published'] if self._iam_publisher() else self.shared.stats['consumed']
        self.shared.log.info('{0} {1}: {2} {3} msgs in {4:0.2f} hours'.format(self.__class__.__name__,
                                                                              self.name,
                                                                              self.msgdo,
                                                                              nmsg,
                                                                              hours))

    def _reset(self):
        if self._iam_publisher():
            self.shared.stats['published'] = 0
        else:
            self.shared.stats['consumed'] = 0

    def _iam_publisher(self):
        if 'Publish' in self.__class__.__name__:
            return True
        else:
            return False

    def stat_reset(self):
        self._stat_msg(self.shared.general['statseveryhour'])
        self._reset()
        self.laststattime = time.time()

    def stats(self):
        sincelaststat = time.time() - self.laststattime
        self._stat_msg(sincelaststat/3600)

class Reset(Thread):
    """
       Reset helper thread that resets counters representing published and
       consumed number of messages for each worker.
    """
    def __init__(self, events, map):
        Thread.__init__(self)
        self.events = events
        self.shared = Shared()
        self.map = map
        if not self.shared.runtime['daemonized']:
            self.daemon = True
        self.init_lastreset()
        self.start()

    def init_lastreset(self):
        self.last_reset = copy.copy(self.map)
        now = int(time.time())
        for k, v in self.last_reset.iteritems():
            self.last_reset[k] = now

    def run(self):
        while True:
            if self.events['termth-stats'].is_set():
                break
            now = int(time.time())
            for k, v in self.last_reset.iteritems():
                if now - self.last_reset[k] >= int(k) * 60:
                    for what in ['consumed', 'published']:
                        for w in self.shared.workers:
                            idx = self.map[k]
                            self.shared.statint[w][what][idx] = 0
                    self.last_reset[k] = now

            time.sleep(self.shared.runtime['evsleep'])

class StatSock(Process):
    """
       Listen'n'Answer process that listens and parses queries on local socket
       and replies back with answer. Queries are in form of

         "w:<worker>+g:<published/consumed><interval>"

       where for each worker process consumed or published number of messages
       can be asked for interval of last 15, 30, 60, 180, 360, 720 and 1440
       minutes. Answer is served as:

         "w:<worker>+r:<num of messages or error>"
    """
    def __init__(self, events, sock):
        Process.__init__(self)
        self.events = events
        self.shared = Shared()
        self.sock = sock
        self._int2idx = {'15': 0, '30': 1, '60': 2, '180': 3, '360': 4,
                         '720': 5, '1440': 6}
        self.resetth = Reset(events=events, map=self._int2idx)

        try:
            self.sock.listen(1)
        except socket.error as m:
            self.shared.log.error('Cannot initialize Stats socket %s - %s' % (self.shared.general['statsocket'], repr(m)))
            raise SystemExit(1)

    def _cleanup(self):
        self.sock.close()
        os.unlink(self.shared.general['statsocket'])
        raise SystemExit(0)

    def parse_cmd(self, cmd):
        m = re.findall('w:\w+\+g:\w+', cmd)
        queries = list()

        if m:
            for c in m:
                w, g = c.split('+')
                w = w.split(':')[1]
                g = g.split(':')[1]
                r = re.search('([a-zA-Z]+)([0-9]+)', g)
                try:
                    if r:
                        queries.append((w, r.group(1), self._int2idx[r.group(2)]))
                    else:
                        queries.append((w, 'error'))
                except KeyError:
                    queries.append((w, 'error'))

        if len(queries) > 0:
            return queries
        else:
            return False

    def answer(self, query):
        a = ''
        for q in query:
            if q[1] != 'error':
                r = self.shared.get_nmsg_interval(q[0], q[1], q[2])
                a += 'w:%s+r:%s ' % (str(q[0]), str(r))
            else:
                a += 'w:%s+r:error ' % str(q[0])

        return a[:-1]

    def run(self):
        self.poller = select.poll()
        self.poller.register(self.sock.fileno(), select.POLLIN)

        while True:
            try:
                event = self.poller.poll(float(self.shared.runtime['evsleep'] * 1000))
                if len(event) > 0 and event[0][1] & select.POLLIN:
                    conn, addr = self.sock.accept()
                    data = conn.recv(maxcmdlength)
                    q = self.parse_cmd(data)
                    if q:
                        a = self.answer(q)
                        conn.send(a, maxcmdlength)
                if self.events['term-stats'].is_set():
                    self.shared.log.info('Stats received SIGTERM')
                    self.events['term-stats'].clear()
                    self._cleanup()

            except KeyboardInterrupt:
                self._cleanup()
