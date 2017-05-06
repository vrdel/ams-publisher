import avro.schema
import time

from argo_nagios_ams_publisher.publish import FilePublisher, MessagingPublisher
from argo_nagios_ams_publisher.consume import ConsumerQueue
from argo_nagios_ams_publisher.shared import Shared
from multiprocessing import Event, Lock

def init_dirq_consume(workers, log, ev, daemonized):
    evsleep = 2
    consumers = list()

    for w in workers:
        shared = Shared(worker=w)
        if not getattr(shared, 'runtime', False):
            shared.runtime = dict()
        kw = dict()

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

        kw.update({'log': log})
        kw.update({'ev': ev})
        shared.add_event('lck', Lock())
        shared.add_event('usr1', Event())
        shared.add_event('term', Event())
        shared.add_event('giveup', Event())
        shared.runtime.update(evsleep=evsleep)
        shared.runtime.update(daemonized=daemonized)

        consumers.append(ConsumerQueue(log, worker=w))
        if not daemonized:
            consumers[-1].daemon = True
        consumers[-1].start()

    while True:
        for c in consumers:
            if shared.event('giveup', c.name).is_set():
                c.terminate()
                c.join(1)
                shared.event('giveup', c.name).clear()

        if ev['term'].is_set():
            for c in consumers:
                shared.event('term', c.name).set()
                c.join(1)
            raise SystemExit(0)

        if ev['usr1'].is_set():
            for c in consumers:
                shared.event('usr1', c.name).set()
            ev['usr1'].clear()

        try:
            time.sleep(evsleep)
        except KeyboardInterrupt:
            for c in consumers:
                c.join(1)
            raise SystemExit(0)
