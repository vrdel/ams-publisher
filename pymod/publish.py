class Publish(object):
    def __init__(self, *args, **kwargs):
        for d in kwargs['kwargs'].iterkeys():
            code = "self.{0} = kwargs['kwargs']['{0}']".format(d)
            exec code
        self.nmsgs_published = 0

    def stats(self, reset=False):
        self.log.info('{0} {1}: sent {2} msgs in {3} hours'.format(self.__class__.__name__,
                                                                   self.name,
                                                                   self.nmsgs_published,
                                                                   self.statseveryhour
                                                                   ))
        if reset:
            self.nmsgs_published = 0

    def write(self, num=0):
        pass

class FilePublisher(Publish):
    def __init__(self, *args, **kwargs):
        super(FilePublisher, self).__init__(*args, **kwargs)

    def write(self, num=0):
        published = set()
        try:
            for i in range(self.pubnumloop):
                with open('/{0}/{1}'.format(self.writemsgfiledir, self.topic), 'a') as fp:
                    fp.writelines(['{0}\n'.format(str(self.inmemq[e][1]))
                                   for e in range(self.bulk)])
                published.update([self.inmemq[e][0] for e in range(self.bulk)])
                self.nmsgs_published += self.bulk

                self.inmemq.rotate(-self.bulk)

            return True, published

        except Exception as e:
            self.log.error(e)
            return False, published
