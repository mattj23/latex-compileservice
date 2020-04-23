import os
import tempfile
import re
import uuid
import hashlib
import pytest
import redis

from latex.config import TestConfig
from latex.session import Session, SessionManager, to_key, clear_expired_sessions
from latex.services.time_service import TimeService, TestClock

redis_url_pattern = re.compile(r"redis:\/\/:(\S*)@(\S+):(\d+)\/(\d+)")


def find_test_asset_folder() -> str:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(script_dir, "test_files")


def hash_file(path: str) -> str:
    sha = hashlib.sha1()
    with open(path, "rb") as handle:
        data = handle.read()
        sha.update(data)
    return sha.hexdigest()


def unique_key() -> str:
    """ Generates a truncated uuid for convenience """
    return str(uuid.uuid4()).replace("-", "").upper()[:12]


class TestFixture:
    def __init__(self, **kwargs):
        self.client: redis.Redis = kwargs.get("client", None)
        self.instance: str = kwargs.get("instance", unique_key())
        self.manager: SessionManager = kwargs.get("manager", None)
        self.clock: TestClock = kwargs.get("test_clock", None)
        self.time_service: TimeService = kwargs.get("time_service", None)


@pytest.fixture(scope="function")
def fixture() -> TestFixture:
    # Parse the TestConfig's REDIS_URL to extract host, port, db, throw an exception if it
    # doesn't work
    groups = redis_url_pattern.match(TestConfig().REDIS_URL)
    if not groups:
        raise Exception(f"could not parse url {TestConfig().REDIS_URL} into host, port, and database")
    pw, host, port, db = groups.groups()

    # Create the instance key
    instance_key = unique_key()

    # Create the redis client
    client = redis.Redis(host=host, port=int(port), db=int(db))

    # Create the test time service
    clock = TestClock()
    time_service = TimeService(clock)

    # Create the working directory with a context manager so it's automatically
    # cleaned up after the test runs
    with tempfile.TemporaryDirectory(prefix=instance_key) as temp_path:
        manager = SessionManager(client, time_service, instance_key, temp_path)
        manager.session_ttl = 60 * 5
        fixture = TestFixture(client=client,
                              manager=manager,
                              instance=instance_key,
                              test_clock=clock,
                              time_service=time_service)
        yield fixture

    # Clean up any keys in the instance list, if it's still there
    while True:
        element = client.spop(instance_key)
        if element is None:
            break

        element_key = to_key(element.decode())
        client.delete(element_key)


def test_redis_connection_writeable(fixture):
    """ Tests whether the Redis connection is working and using a unique instance """
    initial_read = fixture.client.get(fixture.instance)
    fixture.client.set(fixture.instance, "test value here")
    test_read = fixture.client.get(fixture.instance)
    fixture.client.delete(fixture.instance)
    final_read = fixture.client.get(fixture.instance)

    assert initial_read is None
    assert test_read.decode() == "test value here"
    assert final_read is None


def test_session_key_generated(fixture: TestFixture):
    """ Tests whether the session key contains at least twelve hexadecimal digits """
    sesh = fixture.manager.create_session("pdflatex", "latextest.tex")
    key_pattern = re.compile(r"[0-9a-f]{12}")
    assert key_pattern.findall(sesh.key)


def test_session_saves_to_redis(fixture: TestFixture):
    """ Tests that the session manager is correctly saving a session to the redis store, and
    that the data can be retrieved """
    fixture.clock.set_time(12345)
    original = fixture.manager.create_session("pdflatex", "latextest.tex")
    loaded = fixture.manager.load_session(original.key)
    assert loaded.compiler == original.compiler
    assert loaded.target == original.target
    assert loaded.status == original.status
    assert loaded.created == original.created
    assert original.created == 12345


def test_session_saved_added_to_instance_list(fixture: TestFixture):
    """ Tests that when a session is created, the instance list of sessions now contains
    the new session. Verify that this works with multiple sessions. """
    session = fixture.manager.create_session("pdflatex", "sample1.tex")
    contents = set(x.decode() for x in fixture.client.smembers(fixture.instance))
    assert session.key in contents
    assert len(contents) == 1

    session2 = fixture.manager.create_session("xelatex", "sample1.tex")
    contents = set(x.decode() for x in fixture.client.smembers(fixture.instance))
    assert session.key in contents
    assert session2.key in contents
    assert len(contents) == 2


def test_session_file_saves_to_disk(fixture: TestFixture):
    """ Tests that when a file is added to the session it is saved correctly to the source/
    directory in the working folder (verifies by checksum) """
    target_filename = "sample1.tex"
    source_path = os.path.join(find_test_asset_folder(), target_filename)
    if not os.path.exists(source_path):
        raise Exception(f"Sample file '{source_path}' not found")

    original_hash = hash_file(source_path)

    session = fixture.manager.create_session("pdflatex", target_filename)
    with session.source_files.open(target_filename, "wb") as dest, open(source_path, "rb") as source:
        dest.write(source.read())

    destination = os.path.join(fixture.manager.working_directory, session.key, Session._source_directory, target_filename)
    copied_hash = hash_file(destination)
    assert original_hash == copied_hash


def test_session_deleted_is_gone_from_redis_and_disk(fixture: TestFixture):
    """ Tests that when a session is deleted, its record is no longer accessible via redis
    and its working directory is removed from the disk"""
    original = fixture.manager.create_session("xelatex", "sample1.tex")

    session = fixture.manager.load_session(original.key)
    fixture.manager.delete_session(session)

    reloaded = fixture.manager.load_session(original.key)

    assert reloaded is None
    assert not os.path.exists(session._file_service.root_path)


def test_session_deleted_is_gone_from_instance_list(fixture: TestFixture):
    """ Tests that when a session is deleted its record is no longer present in the
    instance list """
    original = fixture.manager.create_session("xelatex", "sample1.tex")
    session = fixture.manager.load_session(original.key)
    fixture.manager.delete_session(session)

    assert not fixture.client.sismember(fixture.instance, original.key)


def test_clear_expired_sessions_leaves_non_expired(fixture: TestFixture):
    """ Tests that sessions which have been alive for less than the SESSION_TTL_SEC
    value are not cleared by the clearing function """
    sessions = []
    for i in range(3):
        fixture.clock.set_time(i * 60)
        sessions.append(fixture.manager.create_session("xelatex", "sample1.tex"))

    fixture.clock.set_time(4 * 60)

    clear_expired_sessions(fixture.manager.working_directory,
                           fixture.manager.instance_key,
                           time_service=fixture.time_service)
    for s in sessions:
        loaded = fixture.manager.load_session(s.key)
        assert loaded is not None
        assert loaded.key == s.key


def test_clear_expired_sessions_clears_expired(fixture: TestFixture):
    """ Tests that sessions which have been alive for more than the SESSION_TTL_SEC
    value are cleared by the clearing function """
    sessions = []
    for i in range(8):
        fixture.clock.set_time(i * 60)
        sessions.append(fixture.manager.create_session("xelatex", "sample1.tex"))

    alive_time = 60 * 5
    fixture.clock.set_time(fixture.clock.now + 1.0)

    clear_expired_sessions(fixture.manager.working_directory,
                           fixture.manager.instance_key,
                           time_service=fixture.time_service)
    for s in sessions:
        loaded = fixture.manager.load_session(s.key)
        if fixture.clock.now - s.created > alive_time:
            assert loaded is None
        else:
            assert loaded is not None
            assert loaded.key == s.key
