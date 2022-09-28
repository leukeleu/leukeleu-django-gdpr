import unittest

from unittest import TestCase

from leukeleu_django_gdpr.gdpr import Serializer


class SerializerTest(TestCase):
    def test_serializer(self):
        serializer = Serializer()
        serializer.generate_models_list()
        self.assertEqual(
            set(serializer.models.keys()),
            {
                "auth.Group",
                "auth.Permission",
                "custom_users.CustomUser",
                "custom_users.SpecialUser",
            },
        )

    def test_include_without_exclude(self):
        serializer = Serializer(include_list=["custom_users.CustomUser"])
        serializer.generate_models_list()
        self.assertEqual(
            set(serializer.models.keys()),
            {
                "auth.Group",
                "auth.Permission",
                "custom_users.CustomUser",
                "custom_users.SpecialUser",
            },
        )

    def test_exclude(self):
        serializer = Serializer(exclude_list=["custom_users.CustomUser"])
        serializer.generate_models_list()
        self.assertEqual(
            set(serializer.models.keys()),
            {
                "auth.Group",
                "auth.Permission",
                "custom_users.SpecialUser",
            },
        )

    def test_exclude_app(self):
        serializer = Serializer(exclude_list=["custom_users"])
        serializer.generate_models_list()
        self.assertEqual(
            set(serializer.models.keys()),
            {
                "auth.Group",
                "auth.Permission",
            },
        )

    def test_exclude_regex(self):
        serializer = Serializer(exclude_list=[r"custom_users\.Special[A-z]+"])
        serializer.generate_models_list()
        self.assertEqual(
            set(serializer.models.keys()),
            {
                "auth.Group",
                "auth.Permission",
                "custom_users.CustomUser",
            },
        )

    @unittest.skip("TODO: fix this test")
    def test_exclude_with_include(self):
        """
        FIXME:
         This test reveals a bug in the include/exclude logic, which has not been fixed yet;
         if an app is excluded, none of its models will be considered at all,
         so the include_list doesn't function as an override, even though that was intended.
        """
        serializer = Serializer(
            exclude_list=["custom_users"],
            include_list=[r"custom_users\.CustomUser"],
        )
        serializer.generate_models_list()
        self.assertEqual(
            set(serializer.models.keys()),
            {
                "auth.Group",
                "auth.Permission",
                "custom_users.CustomUser",
            },
        )
