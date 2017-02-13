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

conf = '/etc/argo-nagios-ams-publisher/ams-publisher.conf'
logfile = '/var/log/argo-nagios-ams-publisher/ams-publisher.log'

def seteuser(user):
    os.setegid(user.pw_gid)
    os.seteuid(user.pw_uid)

def build_msg(args, *headers):
    msg = Message()
    msg.header = dict()
    msg.body = str()

    timestamp, service, hostname, metric, status = headers

    msg.header.update({'timestamp': timestamp})
    msg.header.update({'service': service})
    msg.header.update({'hostname': hostname})
    msg.header.update({'metric': metric})
    msg.header.update({'status': status})

    for bs in ['summary', 'message', 'vofqan', 'voname', 'roc']:
        code = "msg.body += '%s: ' + args.%s + '\\n' if args.%s else ''" % (bs, bs, bs)
        exec code

    return msg

def main():
    parser = argparse.ArgumentParser()
    lobj = log.Logger(sys.argv[0], logfile)
    logger = lobj.get()
    confopts = config.parse_config(logger)

    parser.add_argument('--queue', required=True, type=str)

    # msg headers
    parser.add_argument('--timestamp', required=True, type=str)
    parser.add_argument('--service', required=True, type=str)
    parser.add_argument('--hostname', required=True, type=str)
    parser.add_argument('--metric', required=True, type=str)
    parser.add_argument('--status', required=True, type=str)

    # msg body
    parser.add_argument('--summary', required=False, type=str)
    parser.add_argument('--message', required=False, type=str)
    parser.add_argument('--vofqan', required=False, type=str)
    parser.add_argument('--voname', required=False, type=str)
    parser.add_argument('--roc', required=False, type=str)

    args = parser.parse_args()

    seteuser(pwd.getpwnam(confopts['general']['runasuser']))

    try:
        granularity = config.get_queue_granul(args.queue)
        mq = DQS(path=args.queue, granularity=granularity)

        if ',' in args.service:
            services = args.service.split(',')
            services = [s.strip() for s in services]
            for service in services:
                msg = build_msg(args, args.timestamp, service, args.hostname, \
                                args.metric, args.status)
                mq.add_message(msg)
        else:
            msg = build_msg(args, args.timestamp, args.service, args.hostname, \
                            args.metric, args.status)
            mq.add_message(msg)

    except MessageError as e:
        logger.error('Error constructing message - %s', repr(e))

    except (OSError, IOError) as e:
        logger.error(e)
        raise SystemExit(1)
