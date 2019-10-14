import os


class ConfigBase:
    DEBUG = False
    TESTING = False
    REDIS_URL = os.environ.get("REDIS_URL") or "redis://:@localhost:6379/0"
    REDIS_SESSION_LIST = os.environ.get("REDIS_SESSION_LIST") or "all_sessions"


class ProductionConfig(ConfigBase):
    pass


class DevelopmentConfig(ConfigBase):
    DEBUG = True


class TestConfig(ConfigBase):
    DEBUG = True
    TESTING = True

