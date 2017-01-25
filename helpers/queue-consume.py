#!/usr/bin/env python

import argparse
import datetime
import messaging.generator as generator
import os
import pprint
import pwd
import random
import sys
import time

from messaging.message import Message
from messaging.error import MessageError
from messaging.queue.dqs import DQS

default_queue = '/var/spool/argo-nagios-ams-publisher/outgoing-messages/'
default_user = 'nagios'

def seteuser(user):
    os.setegid(user.pw_gid)
    os.seteuid(user.pw_uid)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sleep', required=False, default=0, type=float)
    parser.add_argument('--queue', required=False, default=default_queue, type=str)
    parser.add_argument('--runas', required=False, default=default_user, type=str)
    args = parser.parse_args()

    seteuser(pwd.getpwnam(args.runas))

    msgs = []
    mq = DQS(path=args.queue)
    try:
        if args.sleep > 0:
            while True:
                if mq.count() > 0:
                    for name in mq:
                        if mq.lock(name):
                            msgs.append(mq.get_message(name))
                            mq.remove(name)
                    pprint.pprint(msgs)
                time.sleep(args.sleep)

    except KeyboardInterrupt as e:
        raise SystemExit(0)

main()

