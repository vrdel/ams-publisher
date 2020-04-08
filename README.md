# argo-nagios-ams-publisher

## Description 

`argo-nagios-ams-publisher` is a component acting as bridge from Nagios to ARGO Messaging system. It's integral part of software stack running on ARGO monitoring instance and is responsible for forming and dispatching messages that wrap up results of Nagios probes/tests. It is running as a unix daemon and it consists of two subsystems:
- queueing mechanism 
- publishing/dispatching part

Messages are cached in local directory queue with the help of OCSP Nagios calls and each queue is being monitored by the daemon. After configurable amount of accumulated messages, publisher that is associated to queue sends them to ARGO Messaging system and drains the queue. `argo-nagios-ams-publisher` is written in multiprocessing manner so there is support for multiple (consume, publish) pairs where for each, new worker process will be spawned. 

### Features

Some of the main features are:
- efficient and scalable directory based queueing
- configurable number of (consume, publish) pairs - workers
- two type of publishers: metric results and alarms
- avro serialization of metric results
- configurable watch rate for queue
- configurable bulk of messages sent to ARGO Messaging system
- purger that will keep queue only with sound data
- message rate inspection of each worker for monitoring purposes 

## Installation

Component is supported on CentOS 6 and CentOS 7. RPM packages and all needed dependencies are available in ARGO repositories so installation of component simply narrows down to installing a package:

	yum install -y argo-nagios-ams-publisher

Component relies on:
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
| SystemD Unit     | `/usr/lib/systemd/system/ams-publisher.service`    |
| Local caches     | `/var/spool/argo-nagios-ams-publisher/`            |
| Inspection socket| `/var/run/argo-nagios-ams-publisher/sock`          |
| Log files        | `/var/log/argo-nagios-ams-publisher/`              |

## Configuration

Central configuration is in `ams-publisher.conf`. Configuration consists of `[General]` section and `[Queue_<workername>], [Topic_<workername>]` section pairs. 

Eachs `(queue, topic)` section pair designates one worker process. Two sections are linked by giving the same `workername` so `Public_Metrics` is associated to `Queue_Metrics` but not `Queue_MetricsDevel`. Each worker means one new process spawned. One part of the process inspects local on-disk queue with results, forms and accumulates messages into in-memory buffer - consumer. Other part of the worker process dispatchs accumulated messages to ARGO Messaging system when the targeted number is reached - publisher. Publisher part is resilient to network connection problems and it can be configured for arbitrary number of connection retries.

### General section

```
[General] 
Host = NAGIOS.FQDN.EXAMPLE.COM
RunAsUser = nagios
StatsEveryHour = 24
PublishMsgFile = False
PublishMsgFileDir = /published
PublishArgoMessaging = True
TimeZone = UTC
StatSocket = /var/run/argo-nagios-ams-publisher/sock
```

* `Host` - FQDN of ARGO Monitoring instance that will be part of formed messages dispatched to ARGO Messaging system
* `RunAsUser` - component will run with effective UID and GID of given user, usually `nagios`
* `StatsEveryHour` - write periodic report in system logs 
```
2020-04-08 08:53:42 ams-publisher[963]: INFO - Periodic report (every 6.0h)
2020-04-08 08:53:42 ams-publisher[983]: INFO - ConsumerQueue metrics: consumed 45787 msgs in 6.00 hours
2020-04-08 08:53:42 ams-publisher[983]: INFO - MessagingPublisher metrics: sent 45800 msgs in 6.00 hours
2020-04-08 08:53:42 ams-publisher[1005]: INFO - ConsumerQueue metricsdevel: consumed 45787 msgs in 6.00 hours
2020-04-08 08:53:42 ams-publisher[1005]: INFO - MessagingPublisher metricsdevel: sent 45800 msgs in 6.00 hours
2020-04-08 08:53:42 ams-publisher[993]: INFO - ConsumerQueue alarms: consumed 164 msgs in 6.00 hours
2020-04-08 08:53:42 ams-publisher[993]: INFO - MessagingPublisher alarms: sent 164 msgs in 6.00 hours
```
* `PublishMsgFile`, `PublishMsgFileDir` - "file publisher" that is actually only for testing purposes. If enabled, messages will not be dispatched to ARGO Messaging System, instead it will just be appended to plain text file 
* `TimeZone` - construct timestamp of messages with given timezone set
* `StatsSocket` - query socket that is used for inspection of rates of each worker. It used by the `ams-publisher` Nagios probe.

