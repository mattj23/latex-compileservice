import unittest
from latex import create_app
from latex.config import TestConfig


class LatexApiTests(unittest.TestCase):

    def setUp(self) -> None:
        self.app = create_app(TestConfig())
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        pass

    def test_session_endpoint_routes_correctly(self):
        response = self.client.get("/api/sessions", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

