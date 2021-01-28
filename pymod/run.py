import avro.schema
import datetime
import time

from argo_nagios_ams_publisher.publish import FilePublisher, MessagingPublisher
from argo_nagios_ams_publisher.consume import ConsumerQueue
from argo_nagios_ams_publisher.stats import StatSock
from argo_nagios_ams_publisher.shared import Shared
from argo_nagios_ams_publisher.config import parse_config

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

    for worker in workers:
        shared = Shared(worker=worker)

        # Create dictionaries that hold number of (published, consumed) messages
        # in seconds from epoch. Second from epoch is a key and number of
        # (published, consumed) messages in given second is associated value:
        #
        # { int(time.time()): num_of_bulk_msgs, ... }
        #
        # Counter is read on queries from socket.
        # collections.Counter cannot be shared between processes so
        # manager.dict() is used.
        shared.statint[worker]['consumed'] = manager.dict()
        shared.statint[worker]['published'] = manager.dict()
        shared.reload_confopts = manager.dict()

        # Create integer counters that will be shared across spawned processes
        # and that will keep track of number of published and consumed messages.
        # Counter is read on perodic status reports and signal SIGUSR1.
        shared.statint[worker]['consumed_periodic'] = Value('i', 1)
        shared.statint[worker]['published_periodic'] = Value('i', 1)

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

        localevents.update({'lck-' + worker: Lock()})
        localevents.update({'usr1-' + worker: Event()})
        localevents.update({'period-' + worker: Event()})
        localevents.update({'term-' + worker: Event()})
        localevents.update({'termth-' + worker: ThreadEvent()})
        localevents.update({'giveup-' + worker: Event()})
        shared.runtime.update(evsleep=evsleep)
        shared.runtime.update(daemonized=daemonized)

        consumers.append(ConsumerQueue(events=localevents, worker=worker))
        if not daemonized:
            consumers[-1].daemon = False
        consumers[-1].start()

    if worker:
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
            for consumer in consumers:
                localevents['period-' + consumer.name].set()
                prevstattime = int(time.time())

        for consumer in consumers:
            if localevents['giveup-' + consumer.name].is_set():
                consumer.terminate()
                consumer.join(1)
                localevents['giveup-' + consumer.name].clear()

        if shared.event('term').is_set():
            for consumer in consumers:
                localevents['term-' + consumer.name].set()
                localevents['termth-' + consumer.name].set()
                consumer.join(1)
            localevents['term-stats'].set()
            localevents['termth-stats'].set()
            statsp.join(1)
            raise SystemExit(0)

        if shared.event('usr1').is_set():
            shared.log.info('Started %s' % shared.runtime['started'])
            for consumer in consumers:
                localevents['usr1-' + consumer.name].set()
            localevents['usr1-stats'].set()
            shared.event('usr1').clear()

        try:
            time.sleep(evsleep)
        except KeyboardInterrupt:
            for consumer in consumers:
                consumer.join(1)
            statsp.join(1)
            raise SystemExit(0)
