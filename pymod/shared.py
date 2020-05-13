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
            if not getattr(self, 'statint', False):
                self.statint = dict()
            if not getattr(self, 'reload_confopts', False):
                # will be set in init_dir_consume()
                self.reload_confopts = None
            self.workers = self._queues.keys()

        if worker:
            self.worker = worker
            self.queue = self._queues[worker]
            self.topic = self._topics[worker]
            if worker not in self.statint:
                self.statint[worker] = dict(published=None, consumed=None)

    def reload(self):
        queue = self.reload_confopts['queues'][self.worker]
        topic = self.reload_confopts['topics'][self.worker]
        self.queue.update(queue)
        self.topic.update(topic)

    def add_event(self, name, ev):
        if not getattr(self, 'events', False):
            self.events = dict()
        self.events.update({name: ev})

    def add_log(self, logger):
        if not getattr(self, 'log', False):
            self.log = None
        self.log = logger

    def get_nmsg(self, worker, what, interval):
        n = None

        try:
            n = self.statint[worker][what][interval]
        except KeyError as e:
            n = 'error'

        return n

    def event(self, name):
        return self.events.get(name)
