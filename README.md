# argo-nagios-ams-publisher

## Description 

`argo-nagios-ams-publisher` is a component acting as bridge from Nagios to ARGO Messaging system. It's integral part of software stack running on ARGO monitoring instance and is responsible for forming and dispatching messages that wrap up results of Nagios tests. It is running as a unix daemon and it consists of two subsystems:
- queueing mechanism 
- publishing/dispatching part

Messages are cached in local directory queue with the help of OCSP Nagios calls and each queue is being monitored by the daemon. After configurable amount of accumulated messages, publisher that is associated to queue sends them to ARGO Messaging
system and drains the queue. `argo-nagios-ams-publisher` is written in multiprocessing manner so there is support for multiple queue/publish pairs where for each, new worker process will be spawned. 

### Features

Some of the main features are:
- efficient and scalable directory based queueing
- configurable number of queue/publish pairs
- two type of publishers: metric results and alarms
- avro serialization of metric results
- configurable watch rate for queue
- configurable bulk of messages sent to ARGO Messaging system
- purger that will keep queue only with sound data
- message rate inspection of each worker for monitoring purposes 

## Installation

RPM packages and all needed dependencies are available in ARGO repositories so installation of component simply narrows down to installing a package:

	yum install -y argo-nagios-ams-publisher

For its functioning, component depends on:
- `argo-ams-library` - interaction with ARGO Messaging 
- `avro` - avro serialization of messages' payload
- `python-argparse` - ease build and parse of command line arguments
- `python-daemon` - ease daemonizing of component 
- `python-messaging` - CERN's library for directory based caching/queueing 
- `pytz` - timezone manipulation


| File Types       | Destination                                        |
|------------------|----------------------------------------------------|
| Configuration    | `/etc/argo-nagios-ams-publisher/ams-publisher.conf`|
| Daemon component | `/usr/bin/ams-publisherd`                          |
| Cache delivery   | `/usr/bin/ams-alarm-to-queue, ams-metric-to-queue` |
| Init script      | `/etc/init.d/ams-publisher`                        |
| Local caches     | `/var/spool/argo-nagios-ams-publisher/`            |
| Inspection socket| `/var/run/argo-nagios-ams-publisher/sock`          |
| Log files        | `/var/log/argo-nagios-ams-publisher/`              |

## Configuration
