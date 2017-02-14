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
    data_files = [('/etc/argo-nagios-ams-publisher/', glob.glob('config/*.conf')),
                  ('/etc/init.d/', glob.glob('init/ams-publisher'))],
    scripts = glob.glob('bin/*') + glob.glob('helpers/*')
    )
