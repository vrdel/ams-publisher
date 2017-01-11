import logging
import logging.handlers
import sys
import os.path

logname = 'ams-publisher'
logfile = '/var/log/argo-nagios-ams-publisher/ams-publisher.log'

class Logger(object):
    logger = None

    def _init_stdout(self):
        lfs = '%(levelname)s ' + self._caller + ' - %(message)s'
        lf = logging.Formatter(lfs)
        lv = logging.INFO

        logging.basicConfig(format=lfs, level=lv, stream=sys.stdout)
        self.logger = logging.getLogger(logname)

    def _init_syslog(self):
        lfs = '%(name)s[%(process)s]: %(levelname)s ' + self._caller + ' - %(message)s'
        lf = logging.Formatter(lfs)
        lv = logging.INFO

        sh = logging.handlers.SysLogHandler('/dev/log', logging.handlers.SysLogHandler.LOG_USER)
        sh.setFormatter(lf)
        sh.setLevel(lv)
        self.logger.addHandler(sh)

    def _init_filelog(self):
        lfs = '%(asctime)s %(name)s[%(process)s]: %(levelname)s ' + self._caller + ' - %(message)s'
        lf = logging.Formatter(fmt=lfs, datefmt='%Y-%m-%d %H:%M:%S')
        lv = logging.INFO

        sf = logging.handlers.RotatingFileHandler(logfile, maxBytes=1024, backupCount=5)
        self.loghandle = sf.stream
        sf.setFormatter(lf)
        sf.setLevel(lv)
        self.logger.addHandler(sf)

    def __init__(self, caller):
        self._caller = os.path.basename(caller)
        self._init_stdout()
        self._init_filelog()
        self._init_syslog()

    def get(self):
        return self.logger
