from unittest.mock import patch

from django.test import TestCase

from leukeleu_django_gdpr import checks


class TestCheckPiiFields(TestCase):
    def test_no_gdpr_yml(self):
        self.assertEqual(checks.check_pii_stats(None), [checks.I001])

    @patch("leukeleu_django_gdpr.checks.get_pii_stats")
    def test_some_unclassified(self, mock_get_pii_stats):
        mock_get_pii_stats.return_value = {None: 1, True: 1, False: 1}
        self.assertEqual(checks.check_pii_stats(None), [checks.I001])

    @patch("leukeleu_django_gdpr.checks.get_pii_stats")
    def test_all_classified(self, mock_get_pii_stats):
        mock_get_pii_stats.return_value = {None: 0, True: 1, False: 1}
        self.assertEqual(checks.check_pii_stats(None), [])
