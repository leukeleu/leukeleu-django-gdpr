from unittest import mock

from django.test import TestCase

from leukeleu_django_gdpr.anonymize import BaseAnonymizer
from tests.custom_users.models import CustomUser


def _get_models():
    return {
        "custom_users.CustomUser": {
            "fields": {
                "username": {
                    "pii": True,
                },
                "first_name": {
                    "pii": True,
                },
            }
        }
    }


patch_get_models = mock.patch(
    "leukeleu_django_gdpr.anonymize.get_models_from_gdpr_yml",
    return_value=_get_models(),
)


class AnonymizerTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        patch_get_models.start()
        cls.addClassCleanup(patch_get_models.stop)

    def setUp(self):
        self.user = CustomUser.objects.create(username="User", first_name="John")
        self.superuser = CustomUser.objects.create(username="Super", is_superuser=True)
        self.staffuser = CustomUser.objects.create(username="Staff", is_staff=True)

    def test_username_anonymization(self):
        self.assertEqual(self.user.username, "User")
        self.assertEqual(self.superuser.username, "Super")
        self.assertEqual(self.staffuser.username, "Staff")

        BaseAnonymizer().anonymize()

        self.user.refresh_from_db()
        self.superuser.refresh_from_db()
        self.staffuser.refresh_from_db()

        # This should be different now
        self.assertNotEqual(self.user.username, "User")

        # These should still equal the original usernames
        self.assertEqual(self.superuser.username, "Super")
        self.assertEqual(self.staffuser.username, "Staff")

    def test_excluded_fields(self):
        class Anonymizer(BaseAnonymizer):
            excluded_fields = [
                "custom_users.CustomUser.username",
            ]

        self.assertEqual(self.user.username, "User")
        Anonymizer().anonymize()
        self.user.refresh_from_db()

        # This should still equal the original username
        self.assertEqual(self.user.username, "User")

    def test_extra_fieldtypes(self):
        class Anonymizer(BaseAnonymizer):
            extra_fieldtype_overrides = {
                "CharField": lambda: "Foo",
            }

            def get_field_overrides(self):
                return {}

        self.assertEqual(self.user.first_name, "John")
        Anonymizer().anonymize()
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Foo")

    def test_extra_qs_overrides(self):
        class Anonymizer(BaseAnonymizer):
            extra_qs_overrides = {
                # By default superusers would be skipped
                "custom_users.CustomUser": CustomUser._base_manager.all(),
            }

        self.assertEqual(self.superuser.username, "Super")
        Anonymizer().anonymize()
        self.superuser.refresh_from_db()

        # This should be different now
        self.assertNotEqual(self.superuser.username, "Super")

    def test_extra_field_overrides(self):
        class Anonymizer(BaseAnonymizer):
            extra_field_overrides = {
                "custom_users.CustomUser.username": lambda: "Foo",
            }

        self.assertEqual(self.user.username, "User")
        Anonymizer().anonymize()
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "Foo")

    def test_multiple_runs_while_new_data_is_added(self):
        class Anonymizer(BaseAnonymizer):
            extra_qs_overrides = {
                "custom_users.CustomUser": CustomUser._base_manager.all(),
            }

        Anonymizer().anonymize()
        new_user = CustomUser.objects.create(username="NewUser")
        Anonymizer().anonymize()
        new_user.refresh_from_db()
        self.assertNotEqual(new_user.username, "NewUser")
