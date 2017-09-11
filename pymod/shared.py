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
            if not getattr(self.__class__, '_queues', False):
                self.__class__._queues = confopts['queues']
            if not getattr(self.__class__, '_topics', False):
                self.__class__._topics = confopts['topics']
            if not getattr(self.__class__, 'general', False):
                self.__class__.general = confopts['general']
            if not getattr(self.__class__, 'connection', False):
                self.__class__.connection = confopts['connection']
            self.workers = self.__class__._queues.keys()
        if worker:
            self.worker = worker
            self.queue = self.__class__._queues[worker]
            self.topic = self.__class__._topics[worker]

    def add_event(self, name, ev):
        if not getattr(self.__class__, 'events', False):
            self.__class__.events = dict()
        self.__class__.events.update({name: ev})

    def add_log(self, logger):
        if not getattr(self.__class__, 'log', False):
            self.__class__.log= None
        self.__class__.log = logger
        self.log = self.__class__.log

    def event(self, name):
        return self.__class__.events.get(name)
