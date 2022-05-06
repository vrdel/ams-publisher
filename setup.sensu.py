from distutils.core import setup
from distutils.command.build_py import build_py as _build_py
import shutil
import os
import glob


NAME = 'argo-sensu-ams-publisher'


class custom_build(_build_py):
    description='Bridge from Sensu to the ARGO Messaging system',

    def __init__(self, args):
        super(_build_py, self).__init__(args)
        shutil.copy('init/ams-publisher-sensu.service', 'init/ams-publisher.service')
        shutil.copy('ams-publisher.spec', 'argo-sensu-ams-publisher.spec')
        os.symlink('setup.sensu.py', 'setup.py')

        with open('argo-sensu-ams-publisher.spec', 'r') as specfile:
            data = specfile.read()
            data = data.replace('SPECNAME-ams-publisher', NAME)
            data = data.replace('SPECPERM', 'sensu')

        with open('argo-sensu-ams-publisher.spec', 'w') as specfile:
            specfile.write(data)

        self.run_command('build')
        self.run_command('sdist')

        os.remove('init/ams-publisher.service')
        os.remove('argo-sensu-ams-publisher.spec')
        os.remove('setup.py')


def get_ver():
    specfile = glob.glob("*.spec")
    if specfile:
        with open(specfile[0]) as f:
            for line in f:
                if "Version:" in line:
                    return line.split()[1]
    else:
        print(f'Make sure that *.spec is in directory')
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
        'custombuild': custom_build
    }
)
