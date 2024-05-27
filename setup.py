from distutils.core import setup
import platform

NAME = 'ams-publisher'


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
    description='Bridge from Nagios/Sensu to the ARGO Messaging system',
    long_description='Bridge from Nagios/Sensu to the ARGO Messaging system',
    url='https://github.com/ARGOeu/argo-nagios-ams-publisher',
    package_dir={'ams_publisher': 'pymod/'},
    packages=['ams_publisher'],
    data_files=[('/etc/ams-publisher/', ['config/ams-publisher-sensu.conf',
                                         'config/ams-publisher-nagios.conf',
                                         'config/metric_data.avsc']),
                ('/usr/lib/systemd/system/', ['init/ams-publisher-nagios.service',
                                              'init/ams-publisher-sensu.service'])],
    scripts=['bin/ams-metric-to-queue', 'bin/ams-publisherd'])
