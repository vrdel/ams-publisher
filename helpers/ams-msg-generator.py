#!/usr/bin/env python

import argparse
import datetime
import messaging.generator as generator
import os
import pwd
import random
import sys
import time

from messaging.message import Message
from messaging.error import MessageError
from messaging.queue.dqs import DQS

from pytz import timezone, UnknownTimeZoneError

default_queue = '/var/spool/argo-nagios-ams-publisher/outgoing-messages/'
default_user = 'nagios'

def construct_msg(session, bodysize, timezone):
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
        msg.header.update({'timestamp': str(datetime.datetime.now(timezone).strftime('%Y-%m-%dT%H:%M:%SZ'))})
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
    parser.add_argument('--noout', required=False, action='store_true', default=False)
    parser.add_argument('--sleep', required=False, default=0, type=float)
    parser.add_argument('--bodysize', required=False, default=40, type=int)
    parser.add_argument('--timezone', required=False, default='UTC', type=str)
    args = parser.parse_args()

    seteuser(pwd.getpwnam(args.runas))
    try:
        tz = timezone(args.timezone)
    except UnknownTimeZoneError as e:
        print "Timezone not correct"
        raise SystemExit(1)

    mq = DQS(path=args.queue, granularity=args.granularity)

    try:
        if args.num:
            for i in range(args.num):
                msg = construct_msg(args.session, args.bodysize, tz)
                queue_msg(msg, mq)
                if not args.noout:
                    print msg
        else:
            while True:
                msg = construct_msg(args.session, args.bodysize, tz)
                queue_msg(msg, mq)
                if not args.noout:
                    print msg
                if args.sleep:
                    time.sleep(args.sleep)

    except KeyboardInterrupt as e:
        raise SystemExit(0)

main()
