#!/usr/bin/python3

import argparse
import datetime
import os
import pprint
import pwd
import random
import sys
import time

from messaging.message import Message
from messaging.error import MessageError
from messaging.queue.dqs import DQS

from collections import deque

default_queue = '/var/spool/argo-nagios-ams-publisher/outgoing-messages/'
default_user = 'nagios'
args = None
cqcalld = 1

def seteuser(user):
    os.setegid(user.pw_gid)
    os.seteuid(user.pw_uid)

def consume_queue(mq, num=0):
    global cqcalld, args
    if not args.noout:
        print('---- MSGS ---- RUN {0} ----'.format(cqcalld))

    i, msgs = 1, deque()
    for name in mq:
        if mq.lock(name):
            msgs.append(mq.get_message(name))
            mq.remove(name)
            if num and i == num:
                break
            i += 1
    else:
        print('{0} empty'.format(mq.path))


    if msgs and not args.noout:
        pprint.pprint(msgs)

    cqcalld += 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sleep', required=False, default=0, type=float)
    parser.add_argument('--queue', required=False, default=default_queue, type=str)
    parser.add_argument('--runas', required=False, default=default_user, type=str)
    parser.add_argument('--purge', required=False, action='store_true', default=False)
    parser.add_argument('--noout', required=False, action='store_true', default=False)
    parser.add_argument('--num', required=False, default=0, type=int)
    global args
    args = parser.parse_args()

    seteuser(pwd.getpwnam(args.runas))

    msgs = []
    mq = DQS(path=args.queue)
    try:
        if args.purge:
            mq.purge()
        if args.sleep > 0:
            while True:
                consume_queue(mq, args.num)
                time.sleep(args.sleep)
        else:
            consume_queue(mq, args.num)

    except KeyboardInterrupt as e:
        raise SystemExit(0)

main()

