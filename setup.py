from distutils.core import setup
import platform

NAME = 'argo-nagios-ams-publisher'

def is_c7():
    dist = platform.dist()
    for e in dist:
        if e.startswith('7'):
            return True
    return False


def get_ver():
    try:
        with open(NAME+'.spec') as f:
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
    description='Bridge from Nagios to the ARGO Messaging system',
    long_description='Bridge from Nagios to the ARGO Messaging system',
    url='https://github.com/ARGOeu/argo-nagios-ams-publisher',
    package_dir={'argo_nagios_ams_publisher': 'pymod/'},
    packages=['argo_nagios_ams_publisher'],
    data_files=[('/etc/argo-nagios-ams-publisher/', ['config/ams-publisher.conf', 'config/metric_data.avsc']),
                ('/usr/lib/systemd/system/', ['init/ams-publisher.service']) if is_c7() else \
                ('/etc/init.d/', ['init/ams-publisher'])],
    scripts=['bin/ams-alarm-to-queue', 'bin/ams-metric-to-queue',
             'bin/ams-publisherd', 'helpers/ams-msg-generator.py',
             'helpers/ams-queue-consume.py'])
