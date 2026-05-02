from decimal import Decimal

from django.test import SimpleTestCase

from banking.templatetags.account_tags import format_gbp


class FormatGbpFilterTests(SimpleTestCase):
    def test_quantizes_long_decimal(self):
        self.assertEqual(format_gbp(Decimal("999.9900000000000000")), "999.99")

    def test_none_is_zero(self):
        self.assertEqual(format_gbp(None), "0.00")
