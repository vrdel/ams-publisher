import ConfigParser

conf = '/etc/argo-nagios-ams-publisher/ams-publisher.conf'

def get_queue_granul(queue):
    confopts = parse_config()
    for k, v in confopts['queues'].iteritems():
        if confopts['queues'][k]['queue'].startswith(queue):
            return confopts['queues'][k]['granularity']

def parse_config(logger=None):
    reqsections = set(['queue_', 'topic_', 'general'])
    confopts = dict()

    try:
        config = ConfigParser.ConfigParser()
        if config.read(conf):
            pairedsects = ['{0}_'.format(s.lower().split('_', 1)[0]) for s in config.sections() if '_' in s]

            if len(pairedsects) % 2:
                if logger:
                    logger.error('Unpaired DirQ and Topic sections')
                else:
                    sys.stderr.write('Unpaired DirQ and Topic sections\n')
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
                    confopts['general'].update({'msgavroschema': config.get(section, 'MsgAvroSchema')})
                    confopts['general'].update({'publishretry': int(config.get(section, 'PublishRetry'))})
                    confopts['general'].update({'publishtimeout': int(config.get(section, 'PublishTimeout'))})
                if section.startswith('Queue_'):
                    dirqopts = dict()
                    qname = section.split('_', 1)[1].lower()
                    dirqopts['directory'] = config.get(section, 'Directory')
                    dirqopts['rate'] = int(config.get(section, 'Rate'))
                    dirqopts['purge'] = bool(config.get(section, 'Purge'))
                    dirqopts['purgeeverysec'] = int(config.get(section, 'PurgeEverySec'))
                    dirqopts['maxtemp'] = int(config.get(section, 'MaxTemp'))
                    dirqopts['maxlock'] = int(config.get(section, 'MaxLock'))
                    dirqopts['granularity'] = int(config.get(section, 'Granularity'))
                    queues[qname] = dirqopts
                if section.startswith('Topic_'):
                    topts = dict()
                    tname = section.split('_', 1)[1].lower()
                    topts['host'] = config.get(section, 'Host')
                    topts['type'] = config.get(section, 'Type')
                    topts['key'] = config.get(section, 'Key')
                    topts['project'] = config.get(section, 'Project')
                    topts['topic'] = config.get(section, 'Topic')
                    topts['bulk'] = int(config.get(section, 'BulkSize'))
                    topics[tname] = topts

            for k, v in queues.iteritems():
                if k not in topics:
                    raise ConfigParser.NoSectionError('No topic topic_%s defined' % k)
                    raise SystemExit(1)

                if topics[k]['bulk'] < queues[k]['rate'] and \
                        queues[k]['rate'] % topics[k]['bulk']:
                    if logger:
                        logger.error('queue_%s: Rate should be multiple of BulkSize' % k)
                    else:
                        sys.stderr.write('queue_%s: Rate should be multiple of BulkSize\n' % k)
                    raise SystemExit(1)

            if all([confopts['general']['publishmsgfile'] == False, confopts['general']['publishargomessaging'] == False]):
                if logger:
                    logger.error('One publisher must be enabled')
                else:
                    sys.stderr.write('One publisher must be enabled')
                raise SystemExit(1)

            if all([confopts['general']['publishmsgfile'], confopts['general']['publishargomessaging']]):
                if logger:
                    logger.error('Only one enabled publisher allowed at a time')
                else:
                    sys.stderr.write('Only one enabled publisher allowed at a time')
                raise SystemExit(1)


            confopts['queues'] = queues
            confopts['topics'] = topics
            return confopts

        else:
            if logger:
                logger.error('Missing %s' % conf)
            else:
                sys.stderr.write('Missing %s\n' % conf)
            raise SystemExit(1)

    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError) as e:
        logger.error(e)
        raise SystemExit(1)

    except (ConfigParser.MissingSectionHeaderError, ConfigParser.ParsingError, SystemExit) as e:
        if getattr(e, 'filename', False):
            if logger:
                logger.error(e.filename + ' is not a valid configuration file')
                logger.error(' '.join(e.args))
            else:
                sys.stderr.write(e.filename + ' is not a valid configuration file\n')
                sys.stderr.write(' '.join(e.args) + '\n')
        raise SystemExit(1)

    return confopts
