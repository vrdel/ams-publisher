#!/usr/bin/env python

from messaging.message import Message
from messaging.error import MessageError
from messaging.queue.dqs import DQS

from argo_nagios_ams_publisher import config
from argo_nagios_ams_publisher import log

import argparse
import sys

conf = '/etc/argo-nagios-ams-publisher/ams-publisher.conf'

def main():
    parser = argparse.ArgumentParser()
    lobj = log.Logger(sys.argv[0])
    logger = lobj.get()
    confopts = config.parse_config(conf, logger)

    # msg headers
    parser.add_argument('--timestamp', required=True, type=str)
    parser.add_argument('--service', required=True, type=str)
    parser.add_argument('--hostname', required=True, type=str)
    parser.add_argument('--metric', required=True, type=str)
    parser.add_argument('--status', required=True, type=str)

    # msg body
    parser.add_argument('--summary', required=False, type=str)
    parser.add_argument('--message', required=False, type=str)
    parser.add_argument('--voqan', required=False, type=str)
    parser.add_argument('--voname', required=False, type=str)
    parser.add_argument('--roc', required=False, type=str)

    args = parser.parse_args()

    try:
        msg = Message()
        msg.header = dict()
        msg.body = str()

        msg.header.update({'timestamp': args.timestamp})
        msg.header.update({'service': args.service})
        msg.header.update({'hostname': args.hostname})
        msg.header.update({'metric': args.metric})
        msg.header.update({'status': args.status})

        for bs in ['summary', 'message', 'voqan', 'voname', 'roc']:
            code = "msg.body += '%s: ' + args.%s + '\\n' if args.%s else ''" % (bs, bs, bs)
            exec code

    except MessageError as e:
        logger.error('Error constructing message - %s', repr(e))

    else:
        mq = DQS(path=confopts['queue'])
        mq.add_message(msg)

main()
