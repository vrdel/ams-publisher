import avro.schema
import datetime
import time

from argo_nagios_ams_publisher.publish import FilePublisher, MessagingPublisher
from argo_nagios_ams_publisher.consume import ConsumerQueue
from argo_nagios_ams_publisher.stats import StatSock
from argo_nagios_ams_publisher.shared import Shared
from multiprocessing import Event, Lock, Value, Manager
from threading import Event as ThreadEvent

def init_dirq_consume(workers, daemonized, sockstat):
    """
       Initialize local cache/directory queue consumers. For each Queue defined
       in configuration, one worker process will be spawned and Publisher will
       be associated. Additional one process will be spawned to listen for
       queries on the socket. Register also local SIGTERM and SIGUSR events
       that will be triggered upon receiving same signals from daemon control
       process and that will be used to control the behaviour of spawned
       subprocesses and threads.
    """
    evsleep = 2
    consumers = list()
    localevents = dict()
    manager = Manager()

    for w in workers:
        shared = Shared(worker=w)

        # Create dictionaries that hold number of (published, consumed) messages
        # in seconds from epoch. Second from epoch is a key and number of
        # (published, consumed) messages in given second is associated value:
        #
        # { int(time.time()): num_of_bulk_msgs, ... }
        #
        # Counter is read on queries from socket.
        # collections.Counter cannot be shared between processes so
        # manager.dict() is used.
        shared.statint[w]['consumed'] = manager.dict()
        shared.statint[w]['published'] = manager.dict()

        # Create integer counters that will be shared across spawned processes
        # and that will keep track of number of published and consumed messages.
        # Counter is read on perodic status reports and signal SIGUSR1.
        shared.statint[w]['consumed_periodic'] = Value('i', 1)
        shared.statint[w]['published_periodic'] = Value('i', 1)

        if not getattr(shared, 'runtime', False):
            shared.runtime = dict()
            shared.runtime['started'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            shared.runtime['started_epoch'] = str(int(time.time()))

        if shared.general['publishmsgfile']:
            shared.runtime.update(publisher=FilePublisher)

        if shared.general['publishargomessaging']:
            try:
                if shared.topic['avro']:
                    avsc = open(shared.topic['avroschema'])
                    shared.topic.update(schema=avro.schema.parse(avsc.read()))
            except Exception as e:
                shared.log.error(e)
                raise SystemExit(1)

            shared.runtime.update(publisher=MessagingPublisher)

        localevents.update({'lck-' + w: Lock()})
        localevents.update({'usr1-' + w: Event()})
        localevents.update({'period-' + w: Event()})
        localevents.update({'term-' + w: Event()})
        localevents.update({'termth-' + w: ThreadEvent()})
        localevents.update({'giveup-' + w: Event()})
        shared.runtime.update(evsleep=evsleep)
        shared.runtime.update(daemonized=daemonized)

        consumers.append(ConsumerQueue(events=localevents, worker=w))
        if not daemonized:
            consumers[-1].daemon = False
        consumers[-1].start()

    if w:
        localevents.update({'lck-stats': Lock()})
        localevents.update({'usr1-stats': Event()})
        localevents.update({'term-stats': Event()})
        localevents.update({'termth-stats': ThreadEvent()})
        localevents.update({'giveup-stats': Event()})
        statsp = StatSock(events=localevents, sock=sockstat)
        statsp.daemon = False
        statsp.start()

    prevstattime = int(time.time())
    while True:
        if int(time.time()) - prevstattime >= shared.general['statseveryhour'] * 3600:
            shared.log.info('Periodic report (every %sh)' % shared.general['statseveryhour'])
            for c in consumers:
                localevents['period-' + c.name].set()
                prevstattime = int(time.time())

        for c in consumers:
            if localevents['giveup-' + c.name].is_set():
                c.terminate()
                c.join(1)
                localevents['giveup-' + c.name].clear()

        if shared.event('term').is_set():
            for c in consumers:
                localevents['term-' + c.name].set()
                localevents['termth-' + c.name].set()
                c.join(1)
            localevents['term-stats'].set()
            localevents['termth-stats'].set()
            statsp.join(1)
            raise SystemExit(0)

        if shared.event('usr1').is_set():
            shared.log.info('Started %s' % shared.runtime['started'])
            for c in consumers:
                localevents['usr1-' + c.name].set()
            localevents['usr1-stats'].set()
            shared.event('usr1').clear()

        try:
            time.sleep(evsleep)
        except KeyboardInterrupt:
            for c in consumers:
                c.join(1)
            statsp.join(1)
            raise SystemExit(0)
