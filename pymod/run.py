import decimal
import avro.schema
import os
import time

from argo_nagios_ams_publisher.publish import FilePublisher, MessagingPublisher
from argo_nagios_ams_publisher.consume import ConsumerQueue
from argo_nagios_ams_publisher.shared import Shared
from collections import deque
from datetime import datetime
from multiprocessing import Event, Lock
from threading import Event as ThreadEvent

def init_dirq_consume(workers, log, globevents, daemonized):
    evsleep = 2
    consumers = list()
    localevents = dict()

    for w in workers:
        shared = Shared(worker=w)
        if not getattr(shared, 'runtime', False):
            shared.runtime = dict()

        if shared.general['publishmsgfile']:
            shared.runtime.update(publisher=FilePublisher)

        if shared.general['publishargomessaging']:
            try:
                avsc = open(shared.general['msgavroschema'])
                shared.runtime.update(schema=avro.schema.parse(avsc.read()))
            except Exception as e:
                log.error(e)
                raise SystemExit(1)

            shared.runtime.update(publisher=MessagingPublisher)

        localevents.update({'lck-'+w: Lock()})
        localevents.update({'usr1-'+w: Event()})
        localevents.update({'term-'+w: Event()})
        localevents.update({'termth-'+w: ThreadEvent()})
        localevents.update({'giveup-'+w: Event()})
        shared.runtime.update(evsleep=evsleep)
        shared.runtime.update(daemonized=daemonized)

        consumers.append(ConsumerQueue(log, events=localevents, worker=w))
        if not daemonized:
            consumers[-1].daemon = True
        consumers[-1].start()

    while True:
        for c in consumers:
            if localevents['giveup-'+c.name].is_set():
                c.terminate()
                c.join(1)
                localevents['giveup-'+c.name].clear()

        if globevents['term'].is_set():
            for c in consumers:
                localevents['term-'+c.name].set()
                localevents['termth-'+c.name].set()
                c.join(1)
            raise SystemExit(0)

        if globevents['usr1'].is_set():
            for c in consumers:
                localevents['usr1-'+c.name].set()
            globevents['usr1'].clear()

        try:
            time.sleep(evsleep)
        except KeyboardInterrupt:
            for c in consumers:
                c.join(1)
            raise SystemExit(0)
