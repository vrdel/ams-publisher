import logging
import logging.handlers
import sys
import os.path

LOGNAME = 'ams-publisher'
LOGFILE = '/var/log/argo-nagios-ams-publisher/ams-publisher.log'


class Logger(object):
    """
       Logger objects with initialized File logger.
    """
    logger = None

    def _init_stdout(self):
        lfs = '%(levelname)s - %(message)s'
        lf = logging.Formatter(lfs)
        lv = logging.INFO

        logging.basicConfig(format=lfs, level=lv, stream=sys.stdout)
        self.logger = logging.getLogger(LOGNAME)

    def _init_filelog(self):
        lfs = '%(asctime)s %(name)s[%(process)s]: %(levelname)s - %(message)s'
        lf = logging.Formatter(fmt=lfs, datefmt='%Y-%m-%d %H:%M:%S')
        lv = logging.INFO

        sf = logging.FileHandler(LOGFILE)
        self.logger.fileloghandle = sf.stream
        sf.setFormatter(lf)
        sf.setLevel(lv)
        self.logger.addHandler(sf)

    def __init__(self, caller):
        self._caller = os.path.basename(caller)
        self._init_stdout()
        try:
            self._init_filelog()
        except (OSError, IOError) as e:
            sys.stderr.write('WARNING ' + self._caller + ' Error initializing loggers - ' + str(e) + '\n')

    def get(self):
        return self.logger
