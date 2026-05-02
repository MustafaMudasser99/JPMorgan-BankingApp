"""Smoke tests for in-app NFC terminal routes."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class NfcTerminalRoutesTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="nfc_tester", password="test-pass-123")

    def test_anonymous_redirects_to_login(self):
        r = Client().get("/banking/nfc/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/banking/login/", r["Location"])

    def test_authenticated_terminal_ok(self):
        c = Client()
        c.force_login(self.user)
        r = c.get("/banking/nfc/")
        self.assertEqual(r.status_code, 200)
        text = r.content.decode().lower()
        self.assertTrue("tap card" in text or "pyscard" in text)

    def test_config_json_requires_login(self):
        r = Client().get("/banking/nfc/config/state/")
        self.assertEqual(r.status_code, 302)
