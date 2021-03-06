import os
import uuid


class ConfigBase:
    DEBUG = False
    TESTING = False
    REDIS_URL = os.environ.get("REDIS_URL") or "redis://:@localhost:6379/0"
    REDIS_SESSION_LIST = os.environ.get("REDIS_SESSION_LIST") or "all_sessions"
    WORKING_DIRECTORY = os.environ.get("WORKING_DIRECTORY") or "/working"
    SESSION_TTL_SEC = os.environ.get("SESSION_TTL_SEC") or 60 * 5
    CLEAR_EXPIRED_INTERVAL_SEC = os.environ.get("CLEAR_EXPIRED_INTERVAL_SEC") or 60
    INSTANCE_KEY = os.environ.get("INSTANCE_KEY") or "latex-compile-service"


class ProductionConfig(ConfigBase):
    pass


class DevelopmentConfig(ConfigBase):
    DEBUG = True


class TestConfig(ConfigBase):
    DEBUG = True
    TESTING = True
    INSTANCE_KEY = str(uuid.uuid4()).replace("-", "")[:10]

