class Shared(object):
    def __new__(cls, *args, **kwargs):
        if getattr(cls, 'sharedobj', False):
            return cls.sharedobj
        else:
            setattr(cls, 'sharedobj', object.__new__(cls))
            return cls.sharedobj

    def __init__(self, confopts=None, worker=None):
        if confopts:
            self._queues = confopts['queues']
            self._topics = confopts['topics']
            self.general = confopts['general']
            self.workers = self._queues.keys()
        if worker:
            self.worker = worker
            self.queue = self._queues[worker]
            self.topic = self._topics[worker]

    def add_event(self, name, ev, glob=False):
        if not getattr(self, 'events', False):
            self.events = dict()
        if glob:
            self.events.update({'{0}-{1}'.format('global', name): ev})
        else:
            self.events.update({'{0}-{1}'.format(self.worker, name): ev})

    def event(self, name, worker=None):
        if not worker:
            return self.events.get('{0}-{1}'.format('global', name))
        else:
            return self.events.get('{0}-{1}'.format(self.worker, name))
