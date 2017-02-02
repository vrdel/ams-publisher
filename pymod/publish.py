class Publish(object):
    def __init__(self, *args, **kwargs):
        for d in kwargs.iterkeys():
            code = "self.{0} = kwargs['{0}']".format(d)
            exec code
        self.init_confopts(kwargs['conf'])

    def init_confopts(self, confopts):
        for k in confopts.iterkeys():
            code = "self.{0} = confopts.get('{0}')".format(k)
            exec code

    def write(self, num=0):
        published = set()
        try:
            for i in range(self.pubnumloop):
                with open('/root/msgs_file', 'a') as fp:
                    fp.writelines(['{0}\n'.format(str(self.inmemq[e][1]))
                                   for e in range(self.msgbulk)])
                published.update([self.inmemq[e][0] for e in range(self.msgbulk)])

                self.inmemq.rotate(-self.msgbulk)

            return True, published

        except Exception as e:
            self.log.error(e)
            return False, published
