# Changelog

## [0.3.8] - 2020-10-08

### Fixed

* remove leftovers from erroneous SIGHUP handling 

## [0.3.7] - 2020-07-08

### Added

* ARGO-844 Complete README for ams-publisher

### Changed

* ARGO-2378 RPM post install should restart service not stop it

## [0.3.6] - 2020-03-31

### Fixed

* ARGO-2224 Local delivery cache tool should pass non-ascii characters

## [0.3.5] - 2019-04-23

### Fixed

- ARGO-1726 Pass site name in metric results
- regression fix to include site name in `site` field of notification

## [0.3.4] - 2019-03-06

### Fixed

* verbose log messages for errors not handled in argo-ams-library

## [0.3.3] - 2019-02-05

### Fixed

* ARGO-1624 Catch all exceptions and warnings from AMS

## [0.3.2] - 2018-11-08

### Added

* ARGO-1348 Descriptive error in case delivery cache tool is called with queue path not specified in configs

### Changed

* ARGO-1408 Ensure correct permissions on pidfile directory

### Fixed

* ARGO-1429 Improved msg counter stats for probe testing purposes

## [0.3.1] - 2018-06-19

### Added

* ARGO-1147 AMS publisher to add optional field

### Changed

* ARGO-1250 Inspection local socket is left with root permissions

### Fixed

* ARGO-986 Purger should not try to remove non-existing cache msg

## [0.3.0] - 2018-03-27

### Added

* ARGO-806 AMS Publisher nagios testing method for upcoming probe
* ARGO-978 Add systemd init script

### Changed

* ARGO-1004 UTC timestamp instead of localtime for dispatched results
* ARGO-1023 Send messages to prod and devel AMS instance in parallel
* ARGO-1084 Connection settings per topic publisher

### Fixed

* ARGO-1051 Ensure service stop called on system shutdown
* ARGO-1055 Last time stats report not updated

## [0.2.1] - 2017-12-20

### Added

* ARGO-700 Delay each msg publish try in case of connection problems

### Fixed

* ARGO-930 Service stop should not depend on successful config parse
* Centos 7 code fixes and spec update

## [0.2.0] - 2017-06-05

### Added

* ARGO-802 Singleton config object with shared config options

### Changed

* ARGO-803 Refactor publisher class
* ARGO-826 Pick up only HARD states

### Fixed

* ARGO-797 argo-nagios-ams-publisher overwrites configuration
* ARGO-815 Sent number of messages reported incorrectly

## [0.1.3] - 2017-04-27

### Fixed

* ARGO-788 Skip empty files/messages

## [0.1.2] - 2017-03-30

### Added

* ARGO-764 Add url_history and url_help message fields for alarms

## [0.1.1] - 2017-03-14

### Added 

* ARGO-732 Structure the body of alarm message as JSON object

## [0.1.0] - 2017-03-01

### Changed

* timestamp is automatically generated and not taken from nagios

### Fixed

* added missing queue spools
* added missing spec dependecies
