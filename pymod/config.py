import ConfigParser

def parse_config(conffile, logger):
    reqsections = set(['dirq_', 'topic_', 'general'])
    confopts = dict()

    try:
        config = ConfigParser.ConfigParser()
        if config.read(conffile):
            pairedsects = ['{0}_'.format(s.lower().split('_', 1)[0]) for s in config.sections() if '_' in s]

            if len(pairedsects) % 2:
                logger.error('Unpaired DirQ and Topic sections')
                raise SystemExit(1)

            commonsects = [s.lower() for s in config.sections() if '_' not in s]
            diff = reqsections.difference(set(commonsects + pairedsects))
            if diff:
                raise ConfigParser.NoSectionError((' '.join(diff)))

            queues, topics = dict(), dict()
            for section in config.sections():
                if section.startswith('General'):
                    confopts['general'] = {'runasuser': config.get(section, 'RunAsUser')}
                if section.startswith('DirQ_'):
                    dirqopts = dict()
                    qname = section.split('_', 1)[1].lower()
                    dirqopts['queue'] = config.get(section, 'Queue')
                    dirqopts['queuerate'] = int(config.get(section, 'QueueRate'))
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
                    topts['key'] = config.get(section, 'Key')
                    topts['project'] = config.get(section, 'Project')
                    topts['topic'] = config.get(section, 'Topic')
                    topts['bulk'] = int(config.get(section, 'BulkSize'))
                    topics[tname] = topts

            for k, v in queues.iteritems():
                if k not in topics:
                    raise ConfigParser.NoSectionError('No topic topic_%s defined' % k)
                    raise SystemExit(1)

                if topics[k]['bulk'] < queues[k]['queuerate'] and \
                        queues[k]['queuerate'] % topics[k]['bulk']:
                    logger.error('dirq_%s: QueueRate should be multiple of BulkSize' % k)
                    raise SystemExit(1)

            confopts['queues'] = queues
            confopts['topics'] = topics
            return confopts

        else:
            logger.error('Missing %s' % conffile)
            raise SystemExit(1)

    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError) as e:
        logger.error(e)
        raise SystemExit(1)

    except (ConfigParser.MissingSectionHeaderError, SystemExit) as e:
        if getattr(e, 'filename', False):
            logger.error(e.filename + ' is not a valid configuration file')
            logger.error(e.message)
        raise SystemExit(1)

    return confopts
