# argo-nagios-ams-publisher

## Introduction 

Bridge from Nagios to the ARGO Messaging system. The argo-nagios-ams-publisher is responsible for handling the nagios messages and publishes them to specific topic to the AMS System.

Until now ARGO uses the nagios-msg component. The msg is responsible for populating the nagios checks with extra information (nagios box, service etc). This component is also using: a)  argo-msg-cache: Component argo-msg-cache retrieves list of message broker URLs from BDII, checks status of each broker and stores brokers to a file, and b) msg-to-handler: Component msg-to-handler subscribes to set topics or queues on message broker and handles messages.  

## Characteristics 

Some of the main characteristics of ams-publisher:

 - Configurable bulk size consume and publish
 - Use of argo-ams-library for publishing to Argo Messaging service
 - Differentiate two types of publishing to AMS: metric_data and alarms
 - Added url_history and url_help message fields for alarms
 - Avro message payload serialization for metric_data publisher
 - Introduce cache producer for alarms
 - Ensure proper cleanup procedures leaving local cache in uncorrupted state
 - On exiting, wait for active publishers to finish

