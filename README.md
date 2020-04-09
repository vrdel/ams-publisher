# argo-nagios-ams-publisher

## Description 

`argo-nagios-ams-publisher` is a component acting as bridge from Nagios to ARGO Messaging system. It's essential part of software stack running on ARGO monitoring instance and is responsible for forming and dispatching messages that wrap up results of Nagios probes/tests. It is running as a unix daemon and it consists of two subsystems:
- queueing mechanism 
- publishing/dispatching part

Messages are cached in local directory queue with the help of OCSP Nagios commands and each queue is being monitored and consumed by the daemon. After configurable amount of accumulated messages, publisher that is associated to queue sends them to ARGO Messaging system and drains the queue. `argo-nagios-ams-publisher` is written in multiprocessing manner so there is support for multiple (consume, publish) pairs where for each, new worker process will be spawned. 

Filling and draining of directory queue is asynchronous. Nagios delivers results on its own constant rate while `argo-nagios-ams-publisher` consume and publish them on its own configurable constant rate. It's important to keep the two rates close enough so that the results don't pile up in the queue and leave it early. Component has a mechanism of inspection of rates and trends over time to keep the constants in sync. Also it's resilient to network issues so it will retry configurable number of times to send a messages to ARGO Messaging system. It's also import to note that consume and publish of the queue is a serial process so if publish is stopped, consume part of the worker will be also stopped. That could lead to pile up of results in the queue and since every result is represented as a one file on the file system, easily exhaustion of free inodes and therefore unusable monitoring instance.

More about [Directory queue design](https://dirq.readthedocs.io/en/latest/queuesimple.html#directory-structure)

### Features

Complete list of features are:
- efficient and scalable directory based queueing
- configurable number of (consume, publish) pairs - workers
- two type of publishers: metric results and alarms
- avro serialization of metric results
- configurable watch rate for queue
- configurable bulk of messages sent to ARGO Messaging system
- configurable retry attempts in case of network connection problems
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


| File Types        | Destination                                        |
|-------------------|----------------------------------------------------|
| Configuration     | `/etc/argo-nagios-ams-publisher/ams-publisher.conf`|
| Daemon component  | `/usr/bin/ams-publisherd`                          |
| Cache delivery    | `/usr/bin/ams-alarm-to-queue, ams-metric-to-queue` |
| Init script (C6)  | `/etc/init.d/ams-publisher`                        |
| SystemD Unit (C7) | `/usr/lib/systemd/system/ams-publisher.service`    |
| Local caches      | `/var/spool/argo-nagios-ams-publisher/`            |
| Inspection socket | `/var/run/argo-nagios-ams-publisher/sock`          |
| Log files         | `/var/log/argo-nagios-ams-publisher/`              |

## Configuration

Central configuration is in `ams-publisher.conf`. Configuration consists of `[General]` section and `[Queue_<workername>], [Topic_<workername>]` section pairs. 

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
* `StatsEveryHour` - write periodic report in system logs. Example is given in [Running](Running) 
* `PublishMsgFile`, `PublishMsgFileDir` - "file publisher" that is actually only for testing purposes. If enabled, messages will not be dispatched to ARGO Messaging System, instead it will just be appended to plain text file 
* `TimeZone` - construct timestamp of messages within specified timezone
* `StatsSocket` - query socket that is used for inspection of rates of each worker. It used by the `ams-publisher` Nagios probe.

### Queue, Topic pair section

Eachs `(queue, topic)` section pair designates one worker process. Two sections are linked by giving the same `workername` so `Public_Metrics` is associated to `Queue_Metrics` but not `Queue_MetricsDevel`. Each worker means one new process spawned. One part of the process inspects local on-disk queue with results, forms and accumulates messages into in-memory buffer - consumer. Other part of the worker process dispatchs accumulated messages to ARGO Messaging system when the targeted number is reached - publisher. Publisher part is resilient to network connection problems and it can be configured for arbitrary number of connection retries.

Example of one such pair:
```
[Queue_Metrics]
Directory = /var/spool/argo-nagios-ams-publisher/metrics/
Rate = 10
Purge = True
PurgeEverySec = 300
MaxTemp = 300
MaxLock = 0
Granularity = 60

[Topic_Metrics]
Host = msg.argo.grnet.gr
Key = AMS_TENANTPROJECT_KEY
Project = NAME_OF_AMS_TENANTPROJECT
Topic = metric_data
Bulksize = 100
MsgType = metric_data
Avro = True
AvroSchema = /etc/argo-nagios-ams-publisher/metric_data.avsc
Retry = 5
Timeout = 60
SleepRetry = 300 
```

* `[Queue_Metrics].Directory` - path of directory queue on the filesystem where local cache delivery tools write results of Nagios tests/probes.
* `[Queue_Metrics].Rate` - local cache inspection rate. 10 means that cache will be inspected 10 times at a second because thats the number of status results expected from Nagios that will be picked up verly early. For low volume tenants this could be a lower number.
* `[Queue_Metrics].Purge,PurgeEverySec,MaxTemp,MaxLock` - purge the staled elements of directory queue every `PurgeEverySec` seconds. It cleans the empty intermediate directories below directory queue path, temporary results that exceeded `MaxTemp` time and locked results that exceeded `MaxLock`. 
> It is advisable to leave `MaxLock = 0` which skips every result that have been transformed into a message and added into in-memory queue, but had not yet been dispatched.
* `[Queue_Metrics].Granularity` - new intermediate directory in the toplevel directory queue path is created every `Granularity` seconds
* `[Topic_Metrics].Host,Key,Project,Topic` - options needed for delivering of messages to ARGO Messaging system. `Host` designates the FQDN, `Key` is authorization token, `Project` represents a tenant name and `Topic` is final destination scoped to tenant
* `[Topic_Metric].Bulksize` - accumulate a bulk of `Bulksize` messages before dispatching them to ARGO Messaging system in one request.
* `[Topic_Metric].MsgType` - string indicating what type of message publisher is sending. It can be `metric_data` or `alarm`
* `[Topic_Metrics].Retry,SleepRetry` - these configures how publisher is resilient to network connection problems and ARGO Messaging system downtimes. Default `5 x 300` means that the publisher worker will be resilient to a minimum of `1500` seconds (25 min) of connection problems retrying `5` times and sleeping aproximately `300` seconds before each next attempt
* `[Topic_Metrics].Timeout` - defines the maximum amount of seconds within which request to ARGO Messaging system must be finalized. Consider raising it up for bigger `Bulksize` number.

## Running

Components needs to be properly configured before starting it. At least one worker must be spawned so at least one directory queue needs to exist, Nagios should deliver results to it and publisher part of the worker needs to be associated to it. Afterward, it's just a matter of starting the service.

CentOS 6:
```
/etc/init.d/ams-publisher start
```

CentOS 7:
```
systemctl start ams-publisher.service
```

Component periodically reports rates of each worker in system logs. It does so every `StatsEveryHour`. 
```
2020-04-08 08:53:42 ams-publisher[963]: INFO - Periodic report (every 6.0h)
2020-04-08 08:53:42 ams-publisher[983]: INFO - ConsumerQueue metrics: consumed 45787 msgs in 6.00 hours
2020-04-08 08:53:42 ams-publisher[983]: INFO - MessagingPublisher metrics: sent 45700 msgs in 6.00 hours
2020-04-08 08:53:42 ams-publisher[1005]: INFO - ConsumerQueue metricsdevel: consumed 45787 msgs in 6.00 hours
2020-04-08 08:53:42 ams-publisher[1005]: INFO - MessagingPublisher metricsdevel: sent 45700 msgs in 6.00 hours
2020-04-08 08:53:42 ams-publisher[993]: INFO - ConsumerQueue alarms: consumed 164 msgs in 6.00 hours
2020-04-08 08:53:42 ams-publisher[993]: INFO - MessagingPublisher alarms: sent 164 msgs in 6.00 hours
```

Check the rates of configured workers for past minutes:
```
% ams-publisherd -q 60
INFO - Asked for statistics for last 60 minutes
INFO - worker:metrics published:8500
INFO - worker:alarms published:26
INFO - worker:metricsdevel published:8500
INFO - worker:metrics consumed:8588
INFO - worker:alarms consumed:26
INFO - worker:metricsdevel consumed:8587
```
