import ConfigParser

def parse_config(conffile, logger):
    reqsections = set(['general', 'ingestion'])
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
                    confopts['queue'] = config.get(section, 'Queue')
                    confopts['runasuser'] = config.get(section, 'RunAsUser')
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
