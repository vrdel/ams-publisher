from types import SimpleNamespace
import select

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


def test_get_nmsg_sums_interval_counters(mocker):
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
    mocker.patch("ams_publisher.stats.time.time", return_value=100)

    assert sock.get_nmsg("metrics", "published", 1) == 6


def test_answer_formats_timestamped_results_and_key_errors(mocker):
    shared = SimpleNamespace(runtime={"started_epoch": "1234"})
    sock = make_statsock(shared)

    def fake_get_nmsg(worker, what, nmin):
        if worker == "missing":
            raise KeyError(worker)
        return 42

    get_nmsg = mocker.patch.object(sock, "get_nmsg", side_effect=fake_get_nmsg)

    assert sock.answer(
        [
            ("metrics", "published", "60"),
            ("bad", "error"),
            ("missing", "consumed", "1"),
        ]
    ) == "t:1234 w:metrics+r:42 w:bad+r:error w:missing+r:error"
    assert get_nmsg.call_args_list == [
        mocker.call("metrics", "published", "60"),
        mocker.call("missing", "consumed", "1"),
    ]


def test_setup_statssocket_replaces_existing_socket_file(mocker, tmp_path):
    sock_path = tmp_path / "stats.sock"
    sock_path.write_text("stale")

    class FakeSocket:
        def bind(self, path):
            sock_path.touch()

    fake_socket = FakeSocket()
    socket_factory = mocker.patch("ams_publisher.stats.socket.socket", return_value=fake_socket)
    chown = mocker.patch(
        "ams_publisher.stats.os.chown",
    )
    bind = mocker.spy(fake_socket, "bind")
    shared = Shared({"queues": {}, "topics": {}, "general": {"statssocket": str(sock_path)}})
    shared.add_log(SimpleNamespace(error=mocker.Mock()))

    sock = setup_statssocket(uid=10, gid=20)

    assert isinstance(sock, FakeSocket)
    assert sock_path.exists()
    socket_factory.assert_called_once()
    bind.assert_called_once_with(str(sock_path))
    chown.assert_called_once_with(str(sock_path), 10, 20)


@pytest.mark.parametrize(
    ("stats_socket", "cmd_length", "timeout"),
    [("/run/ams-publisher/sock", 1024, 180), ("/tmp/custom.sock", 4096, 30)],
)
def test_query_stats_sends_published_and_consumed_queries(mocker, stats_socket, cmd_length, timeout):
    logger = SimpleNamespace(info=mocker.Mock(), error=mocker.Mock())
    Shared(
        {
            "queues": {"metrics": {}, "alarms": {}},
            "topics": {"metrics": {}, "alarms": {}},
            "general": {"statssocket": stats_socket, "statscmdlength": cmd_length,
                        "statssockettimeout": timeout},
        }
    ).add_log(logger)
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

        def sendall(self, data):
            self.sent = data

        def recv(self, max_length):
            self.recv_length = max_length
            return self.response

        def close(self):
            self.closed = True

    sockets = []

    def socket_factory(*args):
        sock = FakeSocket(*args)
        sockets.append(sock)
        return sock

    mocker.patch("ams_publisher.stats.socket.socket", side_effect=socket_factory)

    query_stats(15)

    assert all(sock.path == stats_socket for sock in sockets)
    assert all(sock.timeout == timeout for sock in sockets)
    assert all(sock.recv_length == cmd_length for sock in sockets)

    assert [sock.sent for sock in sockets] == [
        b"w:metrics+g:published15 w:alarms+g:published15 ",
        b"w:metrics+g:consumed15 w:alarms+g:consumed15 ",
    ]
    assert logger.info.call_args_list == [
        mocker.call("worker:metrics published:7"),
        mocker.call("worker:alarms published:2"),
        mocker.call("worker:metrics consumed:8"),
        mocker.call("worker:alarms consumed:3"),
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


def test_statsig_initializes_consumer_and_publisher_counters(mocker):
    mocker.patch("ams_publisher.stats.time.time", return_value=100)
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


def test_statsock_uses_configured_buffer_and_cleans_up_configured_path(mocker):
    shared = Shared({
        "queues": {}, "topics": {},
        "general": {"statssocket": "/tmp/custom.sock", "statscmdlength": 4096},
    })
    shared.runtime = {"evsleep": 0.1, "started_epoch": "123"}
    mocker.patch("ams_publisher.stats.CleanStale")
    poller = mocker.patch("ams_publisher.stats.select.poll").return_value
    poller.poll.side_effect = [[(9, select.POLLIN)], KeyboardInterrupt]
    unlink = mocker.patch("ams_publisher.stats.os.unlink")
    conn = mocker.Mock()
    conn.recv.return_value = b"w:metrics+g:published1"
    listener = mocker.Mock()
    listener.accept.return_value = (conn, None)
    termination = mocker.Mock()
    termination.is_set.return_value = False
    server = StatSock({"term-stats": termination}, listener)
    mocker.patch.object(server, "get_nmsg", return_value=42)

    with pytest.raises(SystemExit) as exc:
        server.run()

    assert exc.value.code == 0
    conn.recv.assert_called_once_with(4096)
    conn.sendall.assert_called_once_with(b"t:123 w:metrics+r:42")
    listener.close.assert_called_once_with()
    unlink.assert_called_once_with("/tmp/custom.sock")
