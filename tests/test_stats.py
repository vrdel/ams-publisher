from types import SimpleNamespace

import pytest

from ams_publisher.shared import Shared
from ams_publisher.stats import StatSig, StatSock, query_stats, setup_statssocket


def make_statsock(shared=None, max_minutes=1440):
    sock = object.__new__(StatSock)
    sock.max_minutes_lookback = max_minutes
    sock.shared = shared
    return sock


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        (b"w:metrics+g:published60", [("metrics", "published", "60")]),
        (b"w:metric-devel+g:consumed5", [("metric-devel", "consumed", "5")]),
        (
            b"w:metrics+g:published60 w:alarms+g:consumed1",
            [("metrics", "published", "60"), ("alarms", "consumed", "1")],
        ),
    ],
)
def test_parse_cmd_accepts_valid_queries(cmd, expected):
    assert make_statsock().parse_cmd(cmd) == expected


@pytest.mark.parametrize(
    "cmd",
    [
        b"",
        b"w:+g:published60",
        b"w:metrics +g:published60",
        b"g:published60",
        b"w:metrics+g:",
    ],
)
def test_parse_cmd_returns_false_when_no_query_matches(cmd):
    assert make_statsock().parse_cmd(cmd) is False


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        (b"w:metrics+g:published1441", [("metrics", "error")]),
        (b"w:metrics+g:published", [("metrics", "error")]),
        (b"w:metrics+g:123", [("metrics", "error")]),
    ],
)
def test_parse_cmd_marks_malformed_or_excessive_lookback_as_error(cmd, expected):
    assert make_statsock().parse_cmd(cmd) == expected


def test_get_nmsg_sums_interval_counters(monkeypatch):
    shared = SimpleNamespace(
        statint={
            "metrics": {
                "published": {
                    100: 1,
                    99: 2,
                    98: 3,
                    40: 100,
                }
            }
        }
    )
    sock = make_statsock(shared)
    monkeypatch.setattr("ams_publisher.stats.time.time", lambda: 100)

    assert sock.get_nmsg("metrics", "published", 1) == 6


def test_answer_formats_timestamped_results_and_key_errors(monkeypatch):
    shared = SimpleNamespace(runtime={"started_epoch": "1234"})
    sock = make_statsock(shared)
    calls = []

    def fake_get_nmsg(worker, what, nmin):
        calls.append((worker, what, nmin))
        if worker == "missing":
            raise KeyError(worker)
        return 42

    monkeypatch.setattr(sock, "get_nmsg", fake_get_nmsg)

    assert sock.answer(
        [
            ("metrics", "published", "60"),
            ("bad", "error"),
            ("missing", "consumed", "1"),
        ]
    ) == "t:1234 w:metrics+r:42 w:bad+r:error w:missing+r:error"
    assert calls == [("metrics", "published", "60"), ("missing", "consumed", "1")]


def test_setup_statssocket_replaces_existing_socket_file(monkeypatch, tmp_path):
    sock_path = tmp_path / "stats.sock"
    sock_path.write_text("stale")
    calls = []

    class FakeSocket:
        def bind(self, path):
            calls.append(("bind", path))
            sock_path.touch()

    monkeypatch.setattr("ams_publisher.stats.STATSOCK", str(sock_path))
    monkeypatch.setattr("ams_publisher.stats.socket.socket", lambda *args: FakeSocket())
    monkeypatch.setattr(
        "ams_publisher.stats.os.chown",
        lambda path, uid, gid: calls.append(("chown", path, uid, gid)),
    )
    shared = Shared({"queues": {}, "topics": {}, "general": {}})
    shared.add_log(SimpleNamespace(error=lambda *args: None))

    sock = setup_statssocket(uid=10, gid=20)

    assert isinstance(sock, FakeSocket)
    assert sock_path.exists()
    assert calls == [("bind", str(sock_path)), ("chown", str(sock_path), 10, 20)]


def test_query_stats_sends_published_and_consumed_queries(monkeypatch):
    logs = []
    Shared(
        {
            "queues": {"metrics": {}, "alarms": {}},
            "topics": {"metrics": {}, "alarms": {}},
            "general": {},
        }
    ).add_log(SimpleNamespace(info=logs.append, error=logs.append))
    sent = []
    responses = [
        b"t:123 w:metrics+r:7 w:alarms+r:2",
        b"t:123 w:metrics+r:8 w:alarms+r:3",
    ]

    class FakeSocket:
        def __init__(self, *args):
            self.response = responses.pop(0)

        def setblocking(self, flag):
            self.blocking = flag

        def settimeout(self, timeout):
            self.timeout = timeout

        def connect(self, path):
            self.path = path

        def send(self, data, max_length):
            sent.append(data)

        def recv(self, max_length):
            return self.response

        def close(self):
            self.closed = True

    monkeypatch.setattr("ams_publisher.stats.socket.socket", FakeSocket)

    query_stats(15)

    assert sent == [
        b"w:metrics+g:published15 w:alarms+g:published15 ",
        b"w:metrics+g:consumed15 w:alarms+g:consumed15 ",
    ]
    assert logs == [
        "worker:metrics published:7",
        "worker:alarms published:2",
        "worker:metrics consumed:8",
        "worker:alarms consumed:3",
    ]


class ConsumerForStats(StatSig):
    shared = SimpleNamespace(
        statint={"worker": {"consumed_periodic": 3}},
        general={"statseveryhour": 2.5},
        log=SimpleNamespace(infos=[]),
    )


class PublishForStats(StatSig):
    shared = SimpleNamespace(
        statint={"worker": {"published_periodic": 4}},
        general={"statseveryhour": 2.5},
        log=SimpleNamespace(infos=[]),
    )


def test_statsig_initializes_consumer_and_publisher_counters(monkeypatch):
    monkeypatch.setattr("ams_publisher.stats.time.time", lambda: 100)
    ConsumerForStats.shared.log.infos = []
    PublishForStats.shared.log.infos = []
    ConsumerForStats.shared.log.info = ConsumerForStats.shared.log.infos.append
    PublishForStats.shared.log.info = PublishForStats.shared.log.infos.append

    consumer = ConsumerForStats("worker")
    publisher = PublishForStats("worker")

    assert consumer.msgdo == "consumed"
    assert publisher.msgdo == "sent"
    assert consumer.shared.statint["worker"]["consumed_periodic"] == 0
    assert publisher.shared.statint["worker"]["published_periodic"] == 0

    consumer.shared.statint["worker"]["consumed_periodic"] = 9
    publisher.shared.statint["worker"]["published_periodic"] = 11
    consumer.stat_reset()
    publisher.stat_reset()

    assert consumer.shared.statint["worker"]["consumed_periodic"] == 0
    assert publisher.shared.statint["worker"]["published_periodic"] == 0
    assert "ConsumerForStats worker: consumed 9 msgs in 2.50 hours" in consumer.shared.log.infos
    assert "PublishForStats worker: sent 11 msgs in 2.50 hours" in publisher.shared.log.infos
