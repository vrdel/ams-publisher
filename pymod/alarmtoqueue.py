#!/usr/bin/env python

from messaging.message import Message
from messaging.error import MessageError
from messaging.queue.dqs import DQS

from argo_nagios_ams_publisher import config
from argo_nagios_ams_publisher import log

import argparse
import datetime
import os
import pwd
import pytz
import sys


CONF = '/etc/argo-nagios-ams-publisher/ams-publisher.conf'


def seteuser(user):
    os.setegid(user.pw_gid)
    os.seteuid(user.pw_uid)


def build_msg(args, *headers):
    msg = Message()
    msg.header = dict()
    msg.body = str()

    timestamp, service, hostname, testname, status, nagioshost = headers

    msg.header.update({'execution_time': timestamp})
    msg.header.update({'service_flavour': service})
    msg.header.update({'node_name': hostname})
    msg.header.update({'test_name': testname})
    msg.header.update({'status': status})

    for bs in ['details', 'vo', 'site', 'roc', 'urlhistory', 'urlhelp']:
        code = "msg.body += '%s: ' + args.%s + '\\n' if args.%s else ''" % (bs, bs, bs)
        exec(code)

    msg.text = True
    return msg


def main():
    parser = argparse.ArgumentParser()
    lobj = log.Logger(sys.argv[0])
    logger = lobj.get()
    confopts = config.parse_config(logger)
    nagioshost = confopts['general']['host']
    tz = pytz.timezone(confopts['general']['timezone'])
    timestamp = datetime.datetime.now(tz).strftime('%Y-%m-%dT%H:%M:%SZ')

    parser.add_argument('--queue', required=True, nargs='+')

    # msg headers
    parser.add_argument('--service', required=True, type=str)
    parser.add_argument('--hostname', required=True, type=str)
    parser.add_argument('--testname', required=True, type=str)
    parser.add_argument('--status', required=True, type=str)

    # msg body
    parser.add_argument('--details', required=False, type=str)
    parser.add_argument('--vo', required=False, type=str)
    parser.add_argument('--site', required=False, type=str)
    parser.add_argument('--roc', required=False, type=str)
    parser.add_argument('--urlhistory', required=False, type=str)
    parser.add_argument('--urlhelp', required=False, type=str)

    args = parser.parse_args()

    seteuser(pwd.getpwnam(confopts['general']['runasuser']))

    try:
        for q in args.queue:
            granularity = config.get_queue_granul(q)
            mq = DQS(path=q, granularity=granularity)

            msg = build_msg(args, timestamp, args.service, args.hostname, \
                            args.testname, args.status, nagioshost)
            mq.add_message(msg)

    except MessageError as e:
        logger.error('Error constructing alarm - %s', repr(e))

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
