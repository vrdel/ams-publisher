#!/usr/bin/env python

from messaging.message import Message
from messaging.error import MessageError
from messaging.queue.dqs import DQS

from argo_nagios_ams_publisher import config
from argo_nagios_ams_publisher import log

import argparse
import os
import pwd
import sys
import datetime
import pytz

conf = '/etc/argo-nagios-ams-publisher/ams-publisher.conf'
logfile = '/var/log/argo-nagios-ams-publisher/ams-publisher.log'


def seteuser(user):
    os.setegid(user.pw_gid)
    os.seteuid(user.pw_uid)


def build_msg(args, *headers):
    msg = Message()
    msg.header = dict()
    msg.body = str()

    timestamp, service, hostname, metric, status, nagioshost = headers

    msg.header.update({'timestamp': timestamp})
    msg.header.update({'service': service})
    msg.header.update({'hostname': hostname})
    msg.header.update({'metric': metric})
    msg.header.update({'status': status})
    msg.header.update({'monitoring_host': nagioshost})

    for bs in ['summary', 'message', 'vofqan', 'voname', 'roc', 'actual_data', 'site']:
        code = "msg.body += '%s: ' + args.%s + '\\n' if args.%s else ''" % (bs, bs, bs)
        exec code

    msg.text = True
    return msg


def main():
    parser = argparse.ArgumentParser()
    lobj = log.Logger(sys.argv[0], logfile)
    logger = lobj.get()
    confopts = config.parse_config(logger)
    nagioshost = confopts['general']['host']
    tz = pytz.timezone(confopts['general']['timezone'])
    timestamp = datetime.datetime.now(tz).strftime('%Y-%m-%dT%H:%M:%SZ')

    parser.add_argument('--servicestatetype', required=True, type=str)
    parser.add_argument('--queue', required=True, nargs='+')

    # msg headers
    parser.add_argument('--service', required=True, type=str)
    parser.add_argument('--hostname', required=True, type=str)
    parser.add_argument('--metric', required=True, type=str)
    parser.add_argument('--status', required=True, type=str)

    # msg body
    parser.add_argument('--actual_data', required=False, type=str)
    parser.add_argument('--message', required=False, type=str)
    parser.add_argument('--roc', required=False, type=str)
    parser.add_argument('--summary', required=False, type=str)
    parser.add_argument('--vofqan', required=False, type=str)
    parser.add_argument('--voname', required=False, type=str)
    parser.add_argument('--site', required=False, type=str)

    args = parser.parse_args()

    seteuser(pwd.getpwnam(confopts['general']['runasuser']))

    if 'HARD' in args.servicestatetype:
        try:
            for q in args.queue:
                granularity = config.get_queue_granul(q)
                mq = DQS(path=q, granularity=granularity)

                if ',' in args.service:
                    services = args.service.split(',')
                    services = [s.strip() for s in services]
                    for service in services:
                        msg = build_msg(args, timestamp, service, args.hostname, \
                                        args.metric, args.status, nagioshost)
                        mq.add_message(msg)
                else:
                    msg = build_msg(args, timestamp, args.service, args.hostname, \
                                    args.metric, args.status, nagioshost)
                    mq.add_message(msg)

        except MessageError as e:
            logger.error('Error constructing metric - %s', repr(e))

        except KeyError:
            logger.error('No configured Queue for directory %s' % q)
            queue_paths = list()
            for (k, v) in confopts['queues'].items():
                queue_paths.append('{0} - {1}'.format(k, v['directory']))
            logger.error('Queues and directories found in config: %s' % ', '.join(queue_paths))
            raise SystemExit(1)

        except (OSError, IOError) as e:
            logger.error(e)
            raise SystemExit(1)
