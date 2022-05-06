from distutils.core import setup
from distutils.command.build_py import build_py as _build_py
import shutil
import os


NAME = 'ams-publisher'


class sensu_build(_build_py):
    description='Bridge from Sensu to the ARGO Messaging system',

    def __init__(self, args):
        super(_build_py, self).__init__(args)
        shutil.copy('init/ams-publisher-sensu.service', 'init/ams-publisher.service')
        self.run_command('build')
        self.run_command('sdist')
        os.remove('init/ams-publisher.service')


class nagios_build(_build_py):
    description='Bridge from Nagios to the ARGO Messaging system',

    def __init__(self, args):
        super(_build_py, self).__init__(args)
        shutil.copy('init/ams-publisher-nagios.service', 'init/ams-publisher.service')
        self.run_command('build')
        self.run_command('sdist')
        os.remove('init/ams-publisher.service')


def get_ver():
    try:
        with open(f'{NAME}.spec') as f:
            for line in f:
                if "Version:" in line:
                    return line.split()[1]
    except IOError:
        print(f'Make sure that {NAME}.spec is in directory')
        raise SystemExit(1)


setup(
    name=NAME,
    version=get_ver(),
    author='SRCE',
    author_email='dvrcic@srce.hr',
    license='ASL 2.0',
    long_description='Bridge from Nagios to the ARGO Messaging system',
    url='https://github.com/ARGOeu/argo-nagios-ams-publisher',
    package_dir={'ams_publisher': 'pymod/'},
    packages=['ams_publisher'],
    data_files=[('/etc/ams-publisher/', ['config/ams-publisher.conf', 'config/metric_data.avsc']),
                ('/usr/lib/systemd/system/', ['init/ams-publisher.service'])],
    scripts=['bin/ams-alarm-to-queue', 'bin/ams-metric-to-queue',
             'bin/ams-publisherd'],
    cmdclass={
        'sensu': sensu_build, 'nagios': nagios_build
    }
)
