# argo-nagios-ams-publisher

## Description 

`argo-nagios-ams-publisher` is component acting as bridge from Nagios to ARGO Messaging system. It's integral part of software stack running on ARGO monitoring instance and is responsible for forming and dispatching messages that are results of Nagios tests. It is running as a unix daemon and it consists of two subsystems:
- queueing mechanism 
- publishing/dispatching part

Messages are cached in local queue with the help of OCSP Nagios calls and each queue is being monitored by the daemon. After configurable amount of accumulated messages, publisher that is associated to queue sends them to ARGO Messaging
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
