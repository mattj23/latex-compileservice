import pytest
import redis
import re
import uuid
from latex.config import TestConfig

redis_url_pattern = re.compile(r"redis:\/\/:(\S*)@(\S+):(\d+)\/(\d+)")


def unique_key() -> str:
    """ Generates a truncated uuid for convenience """
    return str(uuid.uuid4()).replace("-", "").lower()[:12]


class TestFixture:
    def __init__(self, **kwargs):
        self.client: redis.Redis = kwargs.get("client", None)
        self.instance: str = kwargs.get("instance", unique_key())


@pytest.fixture(scope="session")
def fixture() -> TestFixture:
    # Parse the TestConfig's REDIS_URL to extract host, port, db, throw an exception if it
    # doesn't work
    groups = redis_url_pattern.match(TestConfig().REDIS_URL)
    if not groups:
        raise Exception(f"could not parse url {TestConfig().REDIS_URL} into host, port, and database")
    pw, host, port, db = groups.groups()

    # Create the client
    client = redis.Redis(host=host, port=int(port), db=int(db))
    yield TestFixture(client=client)


def test_redis_connection_writeable(fixture):
    initial_read = fixture.client.get(fixture.instance)
    fixture.client.set(fixture.instance, "test value here")
    test_read = fixture.client.get(fixture.instance)
    fixture.client.delete(fixture.instance)
    final_read = fixture.client.get(fixture.instance)

    assert initial_read is None
    assert test_read.decode() == "test value here"
    assert final_read is None
