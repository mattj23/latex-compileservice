import datetime
from flask import Flask


class TimeService:
    def __init__(self):
        self._service: TestClock = None

    @property
    def now(self):
        if self._service is None:
            return datetime.datetime.now().timestamp()
        else:
            return self._service.now

    def init_app(self, app: Flask):
        if app.config["TESTING"]:
            self._service = TestClock()

    @property
    def test(self):
        return self._service


class TestClock:
    def __init__(self, start_time=0):
        self.time = None
        self.set_time(start_time)

    @property
    def now(self):
        return self.time

    def set_time(self, value):
        if type(value) is datetime.datetime:
            self.time = value.timestamp()
        else:
            self.time = value

    def add_time(self, offset: datetime.timedelta):
        start_time = datetime.datetime.fromtimestamp(self.time)
        self.time = (start_time + offset).timestamp()

    def add_seconds(self, seconds):
        self.time += seconds

