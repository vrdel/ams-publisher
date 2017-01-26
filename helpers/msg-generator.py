#!/usr/bin/env python

import argparse
import datetime
import messaging.generator as generator
import random
import sys
import os
import pwd

from messaging.message import Message
from messaging.error import MessageError
from messaging.queue.dqs import DQS

default_queue = '/var/spool/argo-nagios-ams-publisher/outgoing-messages/'
default_user = 'nagios'

def construct_msg(session=None, bodysize=40):
    statusl = ['OK', 'WARNING', 'MISSING', 'CRITICAL', 'UNKNOWN', 'DOWNTIME']

    try:
        msg = Message()
        msg.header = dict()
        msg.body = str()

        if session:
            msg.header.update({'*** SESSION ***': '*** {0} ***'.format(session)})
        msg.header.update({'service': generator.rndb64(10)})
        msg.header.update({'hostname': generator.rndb64(10)})
        msg.header.update({'metric': generator.rndb64(10)})
        msg.header.update({'monitoring_host': generator.rndb64(10)})
        msg.header.update({'timestamp': str(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'))})
        msg.header.update({'status': random.choice(statusl)})

        msg.body += 'summary: %s\n' % generator.rndb64(20)
        msg.body += 'message: %s\n' % generator.rndb64(bodysize)
        msg.body += 'vofqan: %s\n' % generator.rndb64(10)
        msg.body += 'voname: %s\n' % generator.rndb64(3)
        msg.body += 'roc: %s\n' % generator.rndb64(3)

    except MessageError as e:
        sys.stderr.write('Error constructing message - %s\n', repr(e))

    else:
        return msg

def queue_msg(msg, queue):
    try:
        queue.add_message(msg)

    except Exception as e:
        sys.stderr.write(str(e) + '\n')
        raise SystemExit(1)

def seteuser(user):
    os.setegid(user.pw_gid)
    os.seteuid(user.pw_uid)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', required=False, default=str(), type=str)
    parser.add_argument('--num', required=False, default=0, type=int)
    parser.add_argument('--queue', required=False, default=default_queue, type=str)
    parser.add_argument('--granularity', required=False, default=60, type=int)
    parser.add_argument('--runas', required=False, default=default_user, type=str)
    parser.add_argument('--bodysize', required=False, default=40, type=int)
    args = parser.parse_args()

    seteuser(pwd.getpwnam(args.runas))

    mq = DQS(path=args.queue, granularity=args.granularity)

    try:
        if args.num:
            for i in range(args.num):
                msg = construct_msg(args.session, args.bodysize)
                queue_msg(msg, mq)
        else:
            while True:
                msg = construct_msg()
                queue_msg(msg, mq)

    except KeyboardInterrupt as e:
        raise SystemExit(0)

main()
