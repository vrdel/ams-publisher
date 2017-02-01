import ConfigParser

def parse_config(conffile, logger):
    reqsections = set(['dirq', 'messaging', 'general'])
    confopts = dict()

    try:
        config = ConfigParser.ConfigParser()
        if config.read(conffile):
            sections = map(lambda v: v.lower(), config.sections())

            diff = reqsections.difference(sections)
            if diff:
                raise ConfigParser.NoSectionError((' '.join(diff)))

            for section in config.sections():
                if section.startswith('General'):
                    confopts['runasuser'] = config.get(section, 'RunAsUser')
                if section.startswith('DirQ'):
                    confopts['queue'] = config.get(section, 'Queue')
                    confopts['queuerate'] = int(config.get(section, 'QueueRate'))
                    confopts['purge'] = bool(config.get(section, 'Purge'))
                    confopts['purgeeverysec'] = int(config.get(section, 'PurgeEverySec'))
                    confopts['maxtemp'] = int(config.get(section, 'maxtemp'))
                    confopts['maxlock'] = int(config.get(section, 'MaxLock'))
                    confopts['granularity'] = int(config.get(section, 'Granularity'))
                if section.startswith('Messaging'):
                    confopts['msghost'] = config.get(section, 'Host')
                    confopts['msgtoken'] = config.get(section, 'Token')
                    confopts['msgtenant'] = config.get(section, 'Tenant')
                    confopts['msgbulk'] = int(config.get(section, 'BulkSize'))

            if confopts['msgbulk'] < confopts['queuerate'] and \
                    confopts['queuerate'] % confopts['msgbulk']:
                logger.error('QueueRate should be multiple of BulkSize')
                raise SystemExit(1)

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
