import unittest
from flask import Response, Request
from latex import create_app
from latex.config import TestConfig


class LatexApiTests(unittest.TestCase):

    def setUp(self) -> None:
        self.app = create_app(TestConfig())
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        pass

    def test_api_root_endpoint_produces_expected(self):
        response: Response = self.client.get("/api", follow_redirects=True)
        self.assertTrue(response.is_json)
        self.assertIn("create_session", response.json.keys())

    def test_session_endpoint_routes_correctly(self):
        response = self.client.get("/api/sessions", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

