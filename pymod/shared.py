class Shared(object):
    """
       Singleton object used to store configuration options and some runtime
       options that need to be shared throughout the code
    """
    def __new__(cls, *args, **kwargs):
        if getattr(cls, 'sharedobj', False):
            return cls.sharedobj
        else:
            setattr(cls, 'sharedobj', object.__new__(cls))
            return cls.sharedobj

    def __init__(self, confopts=None, worker=None):
        if confopts:
            if not getattr(self, '_queues', False):
                self._queues = confopts['queues']
            if not getattr(self, '_topics', False):
                self._topics = confopts['topics']
            if not getattr(self, 'general', False):
                self.general = confopts['general']
            if not getattr(self, 'connection', False):
                self.connection = confopts['connection']
            if not getattr(self, '_stats', False):
                self._stats = dict()
            self.workers = self._queues.keys()
        if worker:
            self.worker = worker
            self.queue = self._queues[worker]
            self.topic = self._topics[worker]
            if worker not in self._stats:
                self._stats[worker] = dict(published=0)
                self._stats[worker].update(dict(consumed=0))
                for m in ['15', '30', '60', '180', '360', '720', '1440']:
                    codepub = "self._stats[worker].update(dict(published%s=0))" % m
                    codecon = "self._stats[worker].update(dict(consumed%s=0))" % m
                    exec codepub
                    exec codecon
            self.stats = self._stats[worker]


    def add_event(self, name, ev):
        if not getattr(self, 'events', False):
            self.events = dict()
        self.events.update({name: ev})

    def add_log(self, logger):
        if not getattr(self, 'log', False):
            self.log= None
        self.log = logger

    def get_nmsg_interval(self, worker, key):
        return self._stats[worker][key]

    def event(self, name):
        return self.events.get(name)
