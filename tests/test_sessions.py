import os
import tempfile
import re
import uuid

import pytest
import redis

from latex.config import TestConfig
from latex.session import Session

redis_url_pattern = re.compile(r"redis:\/\/:(\S*)@(\S+):(\d+)\/(\d+)")


def unique_key() -> str:
    """ Generates a truncated uuid for convenience """
    return str(uuid.uuid4()).replace("-", "").upper()[:12]


class TestFixture:
    def __init__(self, **kwargs):
        self.client: redis.Redis = kwargs.get("client", None)
        self.instance: str = kwargs.get("instance", unique_key())
        self.path = kwargs["path"]


@pytest.fixture(scope="session")
def fixture() -> TestFixture:
    # Parse the TestConfig's REDIS_URL to extract host, port, db, throw an exception if it
    # doesn't work
    groups = redis_url_pattern.match(TestConfig().REDIS_URL)
    if not groups:
        raise Exception(f"could not parse url {TestConfig().REDIS_URL} into host, port, and database")
    pw, host, port, db = groups.groups()

    # Create the redis client
    client = redis.Redis(host=host, port=int(port), db=int(db))

    # Create the working directory with a context manager so it's automatically
    # cleaned up after the test runs
    with tempfile.TemporaryDirectory() as temp_path:
        fixture = TestFixture(client=client, path=temp_path)
        yield fixture

    # Clean up any keys in the instance list, if it's still there
    remaining = client.get(fixture.instance)
    client.delete(fixture.instance)


def test_redis_connection_writeable(fixture):
    """
    Tests whether the Redis connection is working and using a unique instance
    :param fixture:
    """
    initial_read = fixture.client.get(fixture.instance)
    fixture.client.set(fixture.instance, "test value here")
    test_read = fixture.client.get(fixture.instance)
    fixture.client.delete(fixture.instance)
    final_read = fixture.client.get(fixture.instance)

    assert initial_read is None
    assert test_read.decode() == "test value here"
    assert final_read is None


def test_session_key_generated(fixture):
    sesh = Session.make_new("pdflatex", fixture.instance, fixture.path)
    key_pattern = re.compile(r"[0-9a-f]{12}")
    assert key_pattern.findall(sesh.key)



