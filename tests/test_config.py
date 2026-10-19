import pytest

from ams_publisher import config


def write_config(tmp_path, body):
    path = tmp_path / "ams-publisher.conf"
    path.write_text(body)
    return str(path)


def base_config(**overrides):
    values = {
        "publish_msg_file": "False",
        "publish_argo": "True",
        "bulk": "100",
        "rate": "10",
        "avro": "True",
        "avro_schema": "AvroSchema = /schema.avsc",
        "extra_sections": "",
    }
    values.update(overrides)
    return """
[General]
Host = nagioshost
RunAsUser = nagios
StatsEveryHour = 24
PublishMsgFile = {publish_msg_file}
PublishMsgFileDir = /published
PublishArgoMessaging = {publish_argo}
TimeZone = UTC

[Queue_Metrics-Hyphen-Tenant]
Directory = /var/spool/ams-publisher/metrics/
Rate = {rate}
Purge = True
PurgeEverySec = 300
MaxTemp = 300
MaxLock = 0
Granularity = 60

[Topic_Metrics-Hyphen-Tenant]
Host = messaging.example
Key = EGIKEY
Project = EGI
Bulksize = {bulk}
Topic = metric_data
MsgType = metric_data
Avro = {avro}
{avro_schema}
Retry = 5
Timeout = 60
SleepRetry = 300
{extra_sections}
""".format(**values)


def parse_with_body(mocker, tmp_path, body):
    path = write_config(tmp_path, body)
    mocker.patch.object(config, "get_conffile", return_value=path)
    return config.parse_config()


def test_parse_config_reads_general_queue_and_topic(mocker, tmp_path):
    confopts = parse_with_body(mocker, tmp_path, base_config())

    assert confopts["general"] == {
        "runasuser": "nagios",
        "host": "nagioshost",
        "statseveryhour": 24.0,
        "publishmsgfile": False,
        "publishmsgfiledir": "/published",
        "publishargomessaging": True,
        "timezone": "UTC",
    }
    assert list(confopts["queues"]) == ["metrics-hyphen-tenant"]
    assert confopts["queues"]["metrics-hyphen-tenant"]["directory"] == "/var/spool/ams-publisher/metrics/"
    assert confopts["queues"]["metrics-hyphen-tenant"]["rate"] == 10
    assert confopts["queues"]["metrics-hyphen-tenant"]["purge"] is True
    assert confopts["queues"]["metrics-hyphen-tenant"]["granularity"] == 60
    assert confopts["topics"]["metrics-hyphen-tenant"]["bulk"] == 100
    assert confopts["topics"]["metrics-hyphen-tenant"]["avro"] is True
    assert confopts["topics"]["metrics-hyphen-tenant"]["avroschema"] == "/schema.avsc"


def test_get_queue_granul_matches_directory_prefix(mocker):
    mocker.patch.object(
        config,
        "parse_config",
        return_value={
            "queues": {
                "metrics": {"directory": "/var/spool/metrics/", "granularity": 60},
                "alarms": {"directory": "/var/spool/alarms/", "granularity": 30},
            }
        },
    )

    assert config.get_queue_granul("/var/spool/metrics/") == 60
    assert config.get_queue_granul("/var/spool/alarms") == 30
    with pytest.raises(KeyError):
        config.get_queue_granul("/unknown")


@pytest.mark.parametrize(
    "body",
    [
        base_config(extra_sections="\n[Queue_Alarms]\nDirectory = /alarms\n"),
        base_config(extra_sections="\n[Topic_Alarms]\nHost = messaging.example\n"),
        base_config(publish_msg_file="False", publish_argo="False"),
        base_config(publish_msg_file="True", publish_argo="True"),
        base_config(rate="10", bulk="6"),
        base_config(avro="True", avro_schema=""),
    ],
)
def test_parse_config_exits_for_invalid_configuration(mocker, tmp_path, body):
    with pytest.raises(SystemExit):
        parse_with_body(mocker, tmp_path, body)


def test_get_conffile_returns_first_match(mocker):
    mocker.patch.object(config.glob, "glob", return_value=["/etc/ams-publisher/one.conf"])

    assert config.get_conffile() == "/etc/ams-publisher/one.conf"


def test_get_conffile_exits_when_missing(mocker, capsys):
    mocker.patch.object(config.glob, "glob", return_value=[])

    with pytest.raises(SystemExit):
        config.get_conffile()

    assert "Missing config file" in capsys.readouterr().err
