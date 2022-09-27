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
        serializer = Serializer(exclude_list=[r"custom_users\..*User"])
        serializer.generate_models_list()
        self.assertEqual(
            set(serializer.models.keys()),
            {
                "auth.Group",
                "auth.Permission",
            },
        )

    @unittest.skip("Todo: fix this test")
    def test_exclude_with_include(self):
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
