from types import SimpleNamespace

from ams_publisher.shared import Shared


def confopts():
    return {
        "queues": {"metrics": {"directory": "/queue", "rate": 10}},
        "topics": {"metrics": {"topic": "metric_data", "bulk": 5}},
        "general": {"host": "nagios.example"},
    }


def test_shared_is_singleton_and_initializes_worker_context():
    first = Shared(confopts(), worker="metrics")
    second = Shared()

    assert second is first
    assert first.worker == "metrics"
    assert first.queue == {"directory": "/queue", "rate": 10}
    assert first.topic == {"topic": "metric_data", "bulk": 5}
    assert first.workers == first._queues.keys()
    assert first.statint["metrics"] == {"published": None, "consumed": None}


def test_shared_can_lazily_add_log_and_events():
    shared = Shared(confopts())
    event = object()
    logger = SimpleNamespace(info=lambda *args: None)

    shared.add_event("term", event)
    shared.add_log(logger)

    assert shared.event("term") is event
    assert shared.event("missing") is None
    assert shared.log is logger


def test_shared_reload_updates_current_worker_queue_and_topic():
    shared = Shared(confopts(), worker="metrics")
    shared.reload_confopts = {
        "queues": {"metrics": {"rate": 20, "new": True}},
        "topics": {"metrics": {"bulk": 10}},
    }

    shared.reload()

    assert shared.queue["directory"] == "/queue"
    assert shared.queue["rate"] == 20
    assert shared.queue["new"] is True
    assert shared.topic["topic"] == "metric_data"
    assert shared.topic["bulk"] == 10


def test_shared_get_nmsg_returns_error_for_missing_keys():
    shared = Shared(confopts())
    shared.statint = {"metrics": {"published": {123: 7}}}

    assert shared.get_nmsg("metrics", "published", 123) == 7
    assert shared.get_nmsg("metrics", "consumed", 123) == "error"
    assert shared.get_nmsg("unknown", "published", 123) == "error"
