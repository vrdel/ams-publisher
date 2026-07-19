from collections import deque
from types import SimpleNamespace

from ams_publisher.consume import ConsumerQueue


class FakeDirq:
    def __init__(self, path, names, messages):
        self.path = path
        self.names = names
        self.messages = messages
        self.locked = []
        self.unlocked = []
        self.removed = []

    def __iter__(self):
        return iter(self.names)

    def get_path(self, name):
        return self.path + name + ".lock"

    def lock(self, name):
        self.locked.append(name)
        return True

    def get_message(self, name):
        return self.messages[name]

    def unlock(self, name):
        self.unlocked.append(name)

    def remove(self, name):
        self.removed.append(name)


def make_consumer(tmp_path, names=("one", "two")):
    for name in names:
        (tmp_path / name).write_text("long enough")
    consumer = object.__new__(ConsumerQueue)
    consumer.name = "metrics"
    consumer.inmemq = deque()
    consumer.seenmsgs = set()
    consumer.sess_consumed = 0
    consumer.dirq = FakeDirq(
        str(tmp_path) + "/",
        names,
        {name: "message-" + name for name in names},
    )
    consumer.shared = SimpleNamespace(
        queue={"directory": str(tmp_path) + "/"},
        statint={"metrics": {"consumed": {}, "consumed_periodic": 0}},
        log=SimpleNamespace(errors=[], error=lambda e: None),
    )
    return consumer


def test_consume_dirq_msgs_locks_and_buffers_until_requested_count(monkeypatch, tmp_path):
    consumer = make_consumer(tmp_path)
    monkeypatch.setattr("ams_publisher.consume.time.time", lambda: 200)

    assert consumer.consume_dirq_msgs(2) is True

    assert list(consumer.inmemq) == [("one", "message-one"), ("two", "message-two")]
    assert consumer.dirq.locked == ["one", "two"]
    assert consumer.seenmsgs == set()
    assert consumer.sess_consumed == 0
    assert consumer.shared.statint["metrics"]["consumed"] == {200: 2}
    assert consumer.shared.statint["metrics"]["consumed_periodic"] == 2


def test_consume_dirq_msgs_skips_seen_messages(tmp_path):
    consumer = make_consumer(tmp_path)
    consumer.seenmsgs = {"one"}

    assert consumer.consume_dirq_msgs(1) is True

    assert list(consumer.inmemq) == [("two", "message-two")]
    assert consumer.dirq.locked == ["two"]


def test_unlock_dirq_msgs_accepts_tuples_and_plain_names(tmp_path):
    consumer = make_consumer(tmp_path)
    consumer.inmemq.extend([("one", "message-one"), ("two", "message-two")])

    consumer.unlock_dirq_msgs(["one", ("two", "message-two")])

    assert consumer.dirq.unlocked == ["one", "two"]
    assert list(consumer.inmemq) == []


def test_remove_dirq_msgs_defaults_to_in_memory_queue(tmp_path):
    consumer = make_consumer(tmp_path)
    consumer.inmemq.extend([("one", "message-one"), ("two", "message-two")])

    consumer.remove_dirq_msgs()

    assert consumer.dirq.removed == ["one", "two"]
    assert list(consumer.inmemq) == []
