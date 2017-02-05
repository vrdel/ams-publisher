class Publish(object):
    def __init__(self, *args, **kwargs):
        for d in kwargs['kwargs'].iterkeys():
            code = "self.{0} = kwargs['kwargs']['{0}']".format(d)
            exec code

    def write(self, num=0):
        published = set()
        try:
            for i in range(self.pubnumloop):
                with open('/root/{0}'.format(self.topic), 'a') as fp:
                    fp.writelines(['{0}\n'.format(str(self.inmemq[e][1]))
                                   for e in range(self.bulk)])
                published.update([self.inmemq[e][0] for e in range(self.bulk)])

                self.inmemq.rotate(-self.bulk)

            return True, published

        except Exception as e:
            self.log.error(e)
            return False, published
