class ConfigBase:
    DEBUG = False
    TESTING = False


class ProductionConfig(ConfigBase):
    pass


class DevelopmentConfig(ConfigBase):
    DEBUG = True


class TestConfig(ConfigBase):
    DEBUG = True
    TESTING = True

