import os
import sys
import types

import pytest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PKG = types.ModuleType("ams_publisher")
PKG.__path__ = [os.path.join(ROOT, "pymod")]
sys.modules.setdefault("ams_publisher", PKG)


class StubMessage:
    pass


class StubMessageError(Exception):
    pass


class StubDQS:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class StubDatumWriter:
    def __init__(self, schema):
        self.schema = schema

    def write(self, msg, encoder):
        encoder.write(str(msg).encode())


class StubBinaryEncoder:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)


class StubArgoMessagingService:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.published = []

    def publish(self, topic, msgs, timeout=None):
        self.published.append((topic, msgs, timeout))


class StubAmsMessage:
    def __init__(self, attributes=None, data=None):
        self.attributes = attributes
        self.data = data


def install_stub_modules():
    messaging = types.ModuleType("messaging")
    messaging_message = types.ModuleType("messaging.message")
    messaging_message.Message = StubMessage
    messaging_error = types.ModuleType("messaging.error")
    messaging_error.MessageError = StubMessageError
    messaging_queue = types.ModuleType("messaging.queue")
    messaging_queue_dqs = types.ModuleType("messaging.queue.dqs")
    messaging_queue_dqs.DQS = StubDQS

    avro = types.ModuleType("avro")
    avro_io = types.ModuleType("avro.io")
    avro_io.BinaryEncoder = StubBinaryEncoder
    avro_io.DatumWriter = StubDatumWriter
    avro_schema = types.ModuleType("avro.schema")
    avro_schema.parse = lambda schema: {"schema": schema}
    avro.schema = avro_schema

    argo = types.ModuleType("argo_ams_library")
    argo_ams = types.ModuleType("argo_ams_library.ams")
    argo_ams.ArgoMessagingService = StubArgoMessagingService
    argo_msg = types.ModuleType("argo_ams_library.amsmsg")
    argo_msg.AmsMessage = StubAmsMessage
    argo_exc = types.ModuleType("argo_ams_library.amsexceptions")
    argo_exc.AmsConnectionException = type("AmsConnectionException", (Exception,), {})
    argo_exc.AmsServiceException = type("AmsServiceException", (Exception,), {})
    pytz = types.ModuleType("pytz")
    pytz.UnknownTimeZoneError = type("UnknownTimeZoneError", (Exception,), {})
    pytz.timezone = lambda name: SimpleTimezone(name)

    modules = {
        "messaging": messaging,
        "messaging.message": messaging_message,
        "messaging.error": messaging_error,
        "messaging.queue": messaging_queue,
        "messaging.queue.dqs": messaging_queue_dqs,
        "avro": avro,
        "avro.io": avro_io,
        "avro.schema": avro_schema,
        "argo_ams_library": argo,
        "argo_ams_library.ams": argo_ams,
        "argo_ams_library.amsmsg": argo_msg,
        "argo_ams_library.amsexceptions": argo_exc,
        "pytz": pytz,
    }
    sys.modules.update(modules)


class SimpleTimezone:
    def __init__(self, name):
        self.name = name


install_stub_modules()


@pytest.fixture(autouse=True)
def reset_shared_singleton():
    from ams_publisher.shared import Shared

    if hasattr(Shared, "sharedobj"):
        delattr(Shared, "sharedobj")
    yield
    if hasattr(Shared, "sharedobj"):
        delattr(Shared, "sharedobj")
