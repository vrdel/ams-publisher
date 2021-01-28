import copy
import decimal
import errno
import os
import re
import select
import socket
import time

from threading import Thread
from multiprocessing import Process
from argo_nagios_ams_publisher.shared import Shared

maxcmdlength = 128


def query_stats(last_minutes):
    def parse_result(query):
        try:
            w, r = query.split(b'+')

            w = w.split(b':')[1]
            r = int(r.split(b':')[1])

        except (ValueError, KeyError):
            return (w, 'error')

        return (w, r)

    shared = Shared()

    maxcmdlength = 128
    query_consumed, query_published = '', ''

    for w in shared.workers:
        query_consumed += 'w:{0}+g:consumed{1} '.format(w, last_minutes)

    for w in shared.workers:
        query_published += 'w:{0}+g:published{1} '.format(w, last_minutes)

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.setblocking(0)
        sock.settimeout(15)

        sock.connect(shared.general['statsocket'])
        sock.send(query_published.encode(), maxcmdlength)
        data = sock.recv(maxcmdlength)
        for answer in data.split():
            if answer.startswith(b't:'):
                continue
            w, r = parse_result(answer)
            shared.log.info('worker:{0} published:{1}'.format(w.decode(), r))
        sock.close()

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.setblocking(0)
        sock.settimeout(15)
        sock.connect(shared.general['statsocket'])
        sock.send(query_consumed.encode(), maxcmdlength)
        data = sock.recv(maxcmdlength)
        for answer in data.split(b' '):
            if answer.startswith(b't:'):
                continue
            w, r = parse_result(answer)
            shared.log.info('worker:{0} consumed:{1}'.format(w.decode(), r))
        sock.close()

    except socket.timeout as e:
        shared.log.error('Socket response timeout after 15s')

    except socket.error as e:
        shared.log.error('Socket error: {0}'.format(str(e)))

    finally:
        sock.close()


def setup_statssocket(path, uid, gid):
    shared = Shared()

    if os.path.exists(path):
        os.unlink(path)
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(path)
        os.chown(path, uid, gid)
    except socket.error as e:
        shared.log.error('Error setting up socket: %s - %s' % (path, str(e)))
        raise SystemExit(1)

    return sock


class StatSig(object):
    """
       Class is meant to be subclassed by ConsumerQueue and Publish classes for
       the purpose of implementing common methods that will be called on SIGUSR1
       event and write consumed/published statistics for each worker. Class also
       implements periodic reports.
    """
    def __init__(self, worker):
        self.laststattime = int(time.time())
        self.name = worker
        self.msgdo = 'sent' if self._iam_publisher() else 'consumed'
        self._reset()

    def _stat_msg(self, hours):
        what = 'published_periodic' if self._iam_publisher() else 'consumed_periodic'
        nmsg = self.shared.statint[self.name][what]
        self.shared.log.info('{0} {1}: {2} {3} msgs in {4:0.2f} hours'.format(self.__class__.__name__,
                                                                              self.name,
                                                                              self.msgdo,
                                                                              nmsg,
                                                                              hours))

    def _reset(self):
        if self._iam_publisher():
            self.shared.statint[self.name]['published_periodic'] = 0
        else:
            self.shared.statint[self.name]['consumed_periodic'] = 0

    def _iam_publisher(self):
        return bool('Publish' in self.__class__.__name__)

    def stat_reset(self):
        self._stat_msg(self.shared.general['statseveryhour'])
        self._reset()
        self.laststattime = int(time.time())

    def stats(self):
        sincelaststat = decimal.Decimal(int(time.time()) - self.laststattime)
        self._stat_msg(sincelaststat / decimal.Decimal(3600))


class CleanStale(Thread):
    """
       Helper thread that cleans counters of messages in given epoch second.
       Entries older than minutes_lookback will be discarded.
    """
    def __init__(self, events, minutes_lookback):
        Thread.__init__(self)
        self.events = events
        self.shared = Shared()
        if not self.shared.runtime['daemonized']:
            self.daemon = True
        self.last_reset = int(time.time())
        self.reset_period = minutes_lookback * 60
        self.start()

    def reset_counter(self, counter):
        for e in range(self.now - self.reset_period,
                       self.now - self.reset_period * 2, -1):
            counter.pop(e, 0)

    def run(self):
        while True:
            if self.events['termth-stats'].is_set():
                break
            self.now = int(time.time())
            if self.now - self.last_reset >= self.reset_period:
                for worker in self.shared.workers:
                    for what in ['consumed', 'published']:
                        self.reset_counter(self.shared.statint[worker][what])
                self.last_reset = self.now

            time.sleep(self.shared.runtime['evsleep'])


class StatSock(Process):
    """
       Listen'n'Answer process that listens and parses queries on local socket
       and replies back with answer. Queries are in form of

         "w:<worker>+g:<published/consumed><num_minutes>"

       where for each worker process consumed or published number of messages
       can be asked for arbitrary number of last minutes, max 1440 (24h).
       Answer is served as:

         "t:<start time in epoch seconds> w:<worker>+r:<num of messages or error>"
    """
    def __init__(self, events, sock):
        Process.__init__(self)
        self.poller = select.poll()
        self.events = events
        self.max_minutes_lookback = 1440
        self.shared = Shared()
        self.sock = sock
        self.resetth = CleanStale(events=events,
                                  minutes_lookback=self.max_minutes_lookback)

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
        m = re.findall(r'w:\w+\+g:\w+', cmd.decode())
        queries = list()

        if m:
            for c in m:
                w, g = c.split('+')
                w = w.split(':')[1]
                g = g.split(':')[1]
                r = re.search('([a-zA-Z]+)([0-9]+)', g)
                try:
                    if r:
                        if int(r.group(2)) > self.max_minutes_lookback:
                            queries.append((w, 'error'))
                        else:
                            queries.append((w, r.group(1), r.group(2)))
                    else:
                        queries.append((w, 'error'))
                except KeyError:
                    queries.append((w, 'error'))

        if len(queries) > 0:
            return queries
        else:
            return False

    def get_nmsg(self, worker, what, nmin):
        now = int(time.time())
        count = 0
        for e in range(now, now - int(nmin) * 60, -1):
            count += self.shared.statint[worker][what].get(e, 0)

        return count

    def answer(self, query):
        a = ''
        for q in query:
            try:
                if q[1] != 'error':
                    r = self.get_nmsg(q[0], q[1], q[2])
                    a += 'w:%s+r:%s ' % (str(q[0]), str(r))
                else:
                    a += 'w:%s+r:error ' % str(q[0])
            except KeyError as e:
                a += 'w:%s+r:error ' % str(q[0])
                pass

        a = 't:%s ' % self.shared.runtime['started_epoch'] + a

        return a[:-1]

    def run(self):
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
                        conn.send(a.encode(), maxcmdlength)
                if self.events['term-stats'].is_set():
                    self.shared.log.info('Stats received SIGTERM')
                    self.events['term-stats'].clear()
                    self._cleanup()

            except KeyboardInterrupt:
                self._cleanup()

            except select.error as e:
                if (e[0] == errno.EINTR and
                    self.events['usr1-stats'].is_set()):
                    self.events['usr1-stats'].clear()
