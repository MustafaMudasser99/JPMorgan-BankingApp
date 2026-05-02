"""Tests for payment-system transaction list API."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class PaymentNetworkTransactionsAPITest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="paynet_api_user", password="secret12345")
        self.client = APIClient()

    def test_payment_network_requires_auth(self):
        r = self.client.get("/api/transactions/payment-network/")
        self.assertIn(r.status_code, (401, 403))

    def test_payment_network_authenticated_shape(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.get("/api/transactions/payment-network/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("transactions", r.data)
        self.assertIn("count", r.data)
        self.assertIsInstance(r.data["transactions"], list)
        self.assertEqual(r.data["count"], len(r.data["transactions"]))
