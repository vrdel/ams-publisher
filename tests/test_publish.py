import json
from collections import deque
from types import SimpleNamespace

from ams_publisher.publish import FilePublisher, MessagingPublisher, Publish


def publisher_with_topic(msgtype="metric_data", avro=False):
    publisher = object.__new__(MessagingPublisher)
    publisher.shared = SimpleNamespace(topic={"msgtype": msgtype, "avro": avro})
    return publisher


def test_extract_body_filters_fields_and_applies_name_mapping():
    publisher = publisher_with_topic()

    assert publisher._extract_body(
        "summary: ok\nignored: no\nsite: SITE-A\nbad-line",
        fields=["summary", "site"],
        maps={"site": "endpoint_group"},
    ) == {"summary": "ok", "endpoint_group": "SITE-A"}


def test_body2dict_and_tag2dict_for_metric_data():
    publisher = publisher_with_topic("metric_data")
    body = "\n".join(
        [
            "summary: OK",
            "message: all good",
            "actual_data: 1.0",
            "site: SITE-A",
            "roc: ROC",
            "vofqan: /ops",
            "voname: ops",
            "details: ignored",
        ]
    )

    assert publisher.body2dict(body) == {
        "summary": "OK",
        "message": "all good",
        "actual_data": "1.0",
    }
    assert publisher.tag2dict(body) == {
        "endpoint_group": "SITE-A",
        "roc": "ROC",
        "vofqan": "/ops",
        "voname": "ops",
    }


def test_body2dict_and_tag2dict_for_alarm():
    publisher = publisher_with_topic("alarm")
    body = "\n".join(
        [
            "details: host down",
            "vo: ops",
            "site: SITE-A",
            "roc: ROC",
            "urlhistory: http://history",
            "urlhelp: http://help",
            "summary: ignored",
        ]
    )

    assert publisher.body2dict(body) == {
        "details": "host down",
        "vo": "ops",
        "site": "SITE-A",
        "roc": "ROC",
        "urlhistory": "http://history",
        "urlhelp": "http://help",
    }
    assert publisher.tag2dict(body) == {}


def test_construct_msg_returns_partition_date_and_json_payload():
    publisher = publisher_with_topic("metric_data", avro=False)
    msg = SimpleNamespace(
        header={"timestamp": "2026-07-19T10:11:12Z", "hostname": "host1"},
        body="summary: OK\nsite: SITE-A\nvofqan: /ops\n",
    )

    partition_date, payload = publisher.construct_msg(msg)

    assert partition_date == "2026-07-19"
    assert json.loads(payload) == {
        "timestamp": "2026-07-19T10:11:12Z",
        "hostname": "host1",
        "summary": "OK",
        "tags": {"endpoint_group": "SITE-A", "vofqan": "/ops"},
    }


def test_publish_increments_interval_counters(monkeypatch):
    publisher = object.__new__(Publish)
    publisher.name = "metrics"
    publisher.shared = SimpleNamespace(
        statint={"metrics": {"published": {}, "published_periodic": 0}}
    )
    monkeypatch.setattr("ams_publisher.publish.time.time", lambda: 100)

    publisher._increm_intervalcounters(3)
    publisher._increm_intervalcounters(2)

    assert publisher.shared.statint["metrics"]["published"] == {100: 5}
    assert publisher.shared.statint["metrics"]["published_periodic"] == 5


def test_filepublisher_write_appends_messages_and_rotates_queue(tmp_path):
    publisher = object.__new__(FilePublisher)
    publisher.name = "metrics"
    publisher.pubnumloop = 2
    publisher.inmemq = deque(
        [
            ("one", "msg-one"),
            ("two", "msg-two"),
            ("three", "msg-three"),
            ("four", "msg-four"),
        ]
    )
    publisher.shared = SimpleNamespace(
        general={"publishmsgfiledir": str(tmp_path)},
        topic={"topic": "out.txt", "bulk": 2},
        log=SimpleNamespace(error=lambda *args: None),
    )

    ok, published = publisher.write()

    assert ok is True
    assert published == {"one", "two", "three", "four"}
    assert (tmp_path / "out.txt").read_text().splitlines() == [
        "msg-one",
        "msg-two",
        "msg-three",
        "msg-four",
    ]
