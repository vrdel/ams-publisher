from distutils.core import setup
import glob

NAME='argo-nagios-ams-publisher'

def get_ver():
    try:
        with open(NAME+'.spec') as f:
            for line in f:
                if "Version:" in line:
                    return line.split()[1]
    except IOError:
        print "Make sure that %s is in directory"  % (NAME+'.spec')
        raise SystemExit(1)

setup(
    name = NAME,
    version = get_ver(),
    author = 'SRCE',
    author_email = 'dvrcic@srce.hr',
    license = 'ASL 2.0',
    description = 'Bridge from Nagios to the ARGO Messaging system',
    long_description = 'Bridge from Nagios to the ARGO Messaging system',
    url = 'https://github.com/ARGOeu/argo-nagios-ams-publisher',
    package_dir = {'argo_nagios_ams_publisher': 'pymod/'},
    packages = ['argo_nagios_ams_publisher'],
    data_files = [('/etc/argo-nagios-ams-publisher/', ['config/ams-publisher.conf', 'config/metric_data.avsc']),
                  ('/etc/init.d/', ['init/ams-publisher'])],
    scripts = ['bin/ams-alarm-to-queue', 'bin/ams-metric-to-queue',
               'bin/ams-publisherd', 'helpers/ams-msg-generator.py',
               'helpers/ams-queue-consume.py'])
