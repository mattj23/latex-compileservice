import datetime
from flask import Flask


class TimeService:
    """ The TimeService is a wrapper around the system clock which allows a fake clock to be inserted in the system
    clock's place for unit testing. Avoid any calls directly to datetime.datetime.now(), as they cannot be tested.
    When the TimeService instance is initiated with init_app, a test clock will be substituted for the system clock
    when the app.config's TESTING property is True. """

    def __init__(self, test_clock=None):
        self._service: TestClock = test_clock

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
    """ The TestClock is a fake replacement for the system clock for which the current time can be set externally. The
    internal time is stored as a unix timestamp, and helper methods allow for it to be set and incremented. """

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

