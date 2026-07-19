from types import SimpleNamespace

from ams_publisher import alarmtoqueue, metrictoqueue


def test_alarm_build_msg_sets_headers_body_and_text_flag():
    args = SimpleNamespace(
        details="details text",
        vo="ops",
        site=None,
        roc="ROC",
        urlhistory=None,
        urlhelp="http://help",
    )

    msg = alarmtoqueue.build_msg(
        args,
        "2026-07-19T10:11:12Z",
        "org.nagios",
        "node.example",
        "Check host",
        "CRITICAL",
        "nagios.example",
    )

    assert msg.header == {
        "execution_time": "2026-07-19T10:11:12Z",
        "service_flavour": "org.nagios",
        "node_name": "node.example",
        "test_name": "Check host",
        "status": "CRITICAL",
    }
    assert msg.body == "details: details text\nvo: ops\nroc: ROC\nurlhelp: http://help\n"
    assert msg.text is True


def test_metric_build_msg_sets_headers_body_and_text_flag():
    args = SimpleNamespace(
        summary="OK",
        message="all good",
        vofqan="/ops",
        voname=None,
        roc="ROC",
        actual_data="42",
        site="SITE-A",
    )

    msg = metrictoqueue.build_msg(
        args,
        "2026-07-19T10:11:12Z",
        "org.nagios",
        "node.example",
        "load",
        "OK",
        "nagios.example",
    )

    assert msg.header == {
        "timestamp": "2026-07-19T10:11:12Z",
        "service": "org.nagios",
        "hostname": "node.example",
        "metric": "load",
        "status": "OK",
        "monitoring_host": "nagios.example",
    }
    assert msg.body == (
        "summary: OK\n"
        "message: all good\n"
        "vofqan: /ops\n"
        "roc: ROC\n"
        "actual_data: 42\n"
        "site: SITE-A\n"
    )
    assert msg.text is True


def test_seteuser_switches_effective_uid_and_gid(monkeypatch):
    calls = []
    user = SimpleNamespace(pw_gid=123, pw_uid=456)
    monkeypatch.setattr(alarmtoqueue.os, "setegid", lambda gid: calls.append(("gid", gid)))
    monkeypatch.setattr(alarmtoqueue.os, "seteuid", lambda uid: calls.append(("uid", uid)))

    alarmtoqueue.seteuser(user)

    assert calls == [("gid", 123), ("uid", 456)]
