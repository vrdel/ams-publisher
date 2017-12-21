import logging
import logging.handlers
import sys
import os.path

logname = 'ams-publisher'
logfile = '/var/log/argo-nagios-ams-publisher/ams-publisher.log'

class Logger(object):
    """
       Logger objects with initialized File and Syslog logger.
    """
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

    def _init_filelog(self, logfile):
        lfs = '%(asctime)s %(name)s[%(process)s]: %(levelname)s ' + self._caller + ' - %(message)s'
        lf = logging.Formatter(fmt=lfs, datefmt='%Y-%m-%d %H:%M:%S')
        lv = logging.INFO

        sf = logging.handlers.RotatingFileHandler(logfile, maxBytes=512*1024, backupCount=5)
        self.logger.fileloghandle = sf.stream
        sf.setFormatter(lf)
        sf.setLevel(lv)
        self.logger.addHandler(sf)

    def __init__(self, caller, logfile):
        self._caller = os.path.basename(caller)
        self._init_stdout()
        try:
            self._init_filelog(logfile)
            self._init_syslog()
        except (OSError, IOError) as e:
            sys.stderr.write('WARNING ' + self._caller + ' Error initializing loggers - ' + str(e) + '\n')

    def get(self):
        return self.logger
