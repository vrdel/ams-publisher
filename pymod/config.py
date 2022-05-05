import configparser
import sys
from pytz import timezone, UnknownTimeZoneError

conf = '/etc/ams-publisher/ams-publisher.conf'


def get_queue_granul(queue):
    confopts = parse_config()
    is_queue_found = False

    for k, v in confopts['queues'].items():
        if confopts['queues'][k]['directory'].startswith(queue):
            is_queue_found = True
            break

    if is_queue_found:
        return confopts['queues'][k]['granularity']
    else:
        raise KeyError


def parse_config(logger=None):
    """
       Parse configuration file consisting of one General section and variable
       number of (Queue_<worker>, Topic_<worker>) section pairs
    """
    reqsections = set(['queue_', 'topic_', 'general'])
    confopts = dict()

    try:
        config = configparser.ConfigParser()
        if config.read(conf):
            pairedsects = ['{0}_'.format(s.lower().split('_', 1)[0]) for s in config.sections() if '_' in s]

            if len(pairedsects) % 2:
                if logger:
                    logger.error('Unpaired Queue and Topic sections')
                    raise SystemExit(1)
                else:
                    sys.stderr.write('Unpaired Queue and Topic sections\n')
                    raise SystemExit(1)

            commonsects = [s.lower() for s in config.sections() if '_' not in s]
            diff = reqsections.difference(set(commonsects + pairedsects))
            if diff:
                raise ConfigParser.NoSectionError((' '.join(diff)))

            queues, topics = dict(), dict()
            for section in config.sections():
                if section.startswith('General'):
                    confopts['general'] = ({'runasuser': config.get(section, 'RunAsUser')})
                    confopts['general'].update({'host': config.get(section, 'Host')})
                    confopts['general'].update({'statseveryhour': float(config.get(section, 'StatsEveryHour'))})
                    confopts['general'].update({'publishmsgfile': eval(config.get(section, 'PublishMsgFile'))})
                    confopts['general'].update({'publishmsgfiledir': config.get(section, 'PublishMsgFileDir')})
                    confopts['general'].update({'publishargomessaging': eval(config.get(section, 'PublishArgoMessaging'))})
                    confopts['general'].update({'timezone': config.get(section, 'TimeZone')})
                    try:
                        tz = timezone(confopts['general']['timezone'])
                    except UnknownTimeZoneError as e:
                        if logger:
                            logger.error('Unknown timezone defined: {0}\n'.format(str(e)))
                        else:
                            sys.stderr.write('Unknown timezone defined: {0}\n'.format(str(e)))
                        if reload is False:
                            raise SystemExit(1)

                if section.startswith('Queue_'):
                    dirqopts = dict()
                    qname = section.split('_', 1)[1].lower()
                    dirqopts['directory'] = config.get(section, 'Directory')
                    dirqopts['rate'] = config.getint(section, 'Rate')
                    dirqopts['purge'] = eval(config.get(section, 'Purge').strip())
                    dirqopts['purgeeverysec'] = config.getint(section, 'PurgeEverySec')
                    dirqopts['maxtemp'] = config.getint(section, 'MaxTemp')
                    dirqopts['maxlock'] = config.getint(section, 'MaxLock')
                    dirqopts['granularity'] = config.getint(section, 'Granularity')
                    queues[qname] = dirqopts
                if section.startswith('Topic_'):
                    topts = dict()
                    tname = section.split('_', 1)[1].lower()
                    topts['host'] = config.get(section, 'Host')
                    topts['msgtype'] = config.get(section, 'MsgType')
                    topts['key'] = config.get(section, 'Key')
                    topts['project'] = config.get(section, 'Project')
                    topts['topic'] = config.get(section, 'Topic')
                    topts['bulk'] = config.getint(section, 'BulkSize')
                    topts['avro'] = eval(config.get(section, 'Avro').strip())
                    if topts['avro']:
                        topts['avroschema'] = config.get(section, 'AvroSchema')
                    topts['retry'] = config.getint(section, 'Retry')
                    topts['timeout'] = config.getint(section, 'Timeout')
                    topts['sleepretry'] = config.getint(section, 'SleepRetry')
                    topics[tname] = topts

            for k, v in queues.items():
                if k not in topics:
                    raise configparser.NoSectionError('No topic topic_%s defined' % k)

                if topics[k]['bulk'] < queues[k]['rate'] and \
                        queues[k]['rate'] % topics[k]['bulk']:
                    if logger:
                        logger.error('queue_%s: Rate should be multiple of BulkSize' % k)
                        raise SystemExit(1)
                    else:
                        sys.stderr.write('queue_%s: Rate should be multiple of BulkSize\n' % k)
                        raise SystemExit(1)

                if topics[k]['avro'] and not topics[k].get('avroschema', None):
                    if logger:
                        logger.error('topic_%s: AvroSchema not defined' % k)
                        raise SystemExit(1)
                    else:
                        sys.stderr.write('topic_%s: AvroSchema not defined\n' % k)
                        raise SystemExit(1)

            if all([confopts['general']['publishmsgfile'] is False, confopts['general']['publishargomessaging'] is False]):
                if logger:
                    logger.error('One publisher must be enabled')
                    raise SystemExit(1)
                else:
                    sys.stderr.write('One publisher must be enabled')
                    raise SystemExit(1)

            if all([confopts['general']['publishmsgfile'], confopts['general']['publishargomessaging']]):
                if logger:
                    logger.error('Only one enabled publisher allowed at a time')
                    raise SystemExit(1)
                else:
                    sys.stderr.write('Only one enabled publisher allowed at a time')
                    raise SystemExit(1)

            confopts['queues'] = queues
            confopts['topics'] = topics
            return confopts

        else:
            if logger:
                logger.error('Missing %s' % conf)
                raise SystemExit(1)
            else:
                sys.stderr.write('Missing %s\n' % conf)
                raise SystemExit(1)

    except (configparser.NoOptionError, configparser.NoSectionError) as e:
        if logger:
            logger.error(e)
            raise SystemExit(1)
        else:
            sys.stderr.write(str(e) + '\n')
            raise SystemExit(1)

    except (configparser.MissingSectionHeaderError, configparser.ParsingError, SystemExit) as e:
        if getattr(e, 'filename', False):
            if logger:
                logger.error(e.filename + ' is not a valid configuration file')
                logger.error(' '.join(e.args))
                raise SystemExit(1)
            else:
                sys.stderr.write(e.filename + ' is not a valid configuration file\n')
                sys.stderr.write(' '.join(e.args) + '\n')
                raise SystemExit(1)

    return confopts
