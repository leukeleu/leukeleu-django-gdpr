import pathlib

from django.test import SimpleTestCase as TestCase
from django.test import override_settings

from leukeleu_django_gdpr.gdpr import Serializer, get_gdpr_yml_path


class TestGetGdprYmlPath(TestCase):
    @override_settings(BASE_DIR="/tmp")
    def test_get_gdpr_yml_path(self):
        self.assertEqual(get_gdpr_yml_path(), pathlib.Path("/tmp/gdpr.yml"))

    @override_settings(DJANGO_GDPR_YML_DIR="tests/")
    def test_custom_gdpr_yml_path(self):
        self.assertEqual(get_gdpr_yml_path(), pathlib.Path("tests/gdpr.yml"))


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
                "custom_users.ExclusiveUser",
                "custom_users.SpecialUser",
                # Does not include proxy models:
                # "custom_users.ProxyUser"
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
                "custom_users.ExclusiveUser",
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
                "custom_users.ExclusiveUser",
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
                "custom_users.ExclusiveUser",
            },
        )

    def test_include_django_admin(self):
        """Include a model from django.contrib.admin, even though it is excluded by default."""
        serializer = Serializer(include_list=[r"admin\.LogEntry"])
        serializer.generate_models_list()
        self.assertEqual(
            set(serializer.models.keys()),
            {
                "admin.LogEntry",
                "auth.Group",
                "auth.Permission",
                "custom_users.CustomUser",
                "custom_users.ExclusiveUser",
                "custom_users.SpecialUser",
            },
        )

    def test_exclude_with_include(self):
        """Exclude an app, but include a model and a field from a model in that app."""
        serializer = Serializer(
            exclude_list=["custom_users"],
            include_list=[
                r"custom_users\.CustomUser",
                r"custom_users\.SpecialUser\.username",
            ],
        )
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
        # Still excludes the id and is_pregnant fields from CustomUser because
        # they are default excluded field types. These fields should be
        # explicitly included if needed.
        self.assertNotIn(
            "is_pregnant",
            serializer.models["custom_users.CustomUser"]["fields"].keys(),
        )
        self.assertNotIn(
            "id",
            serializer.models["custom_users.CustomUser"]["fields"].keys(),
        )
        # Only includes the explicitly included username field for SpecialUser
        self.assertEqual(
            set(serializer.models["custom_users.SpecialUser"]["fields"].keys()),
            {"username"},
        )

    def test_include_default_excluded_field(self):
        """Force include fields that are excluded by default."""
        serializer = Serializer(
            include_list=[
                r"custom_users\.CustomUser\.id",
                r"custom_users\.CustomUser\.is_pregnant",
            ],
        )
        serializer.generate_models_list()
        self.assertEqual(
            set(serializer.models.keys()),
            {
                "auth.Group",
                "auth.Permission",
                "custom_users.CustomUser",
                "custom_users.ExclusiveUser",
                "custom_users.SpecialUser",
            },
        )
        # These fields are normally excluded, but are explicitly included here
        self.assertIn(
            "id",
            set(serializer.models["custom_users.CustomUser"]["fields"].keys()),
        )
        self.assertIn(
            "is_pregnant",
            set(serializer.models["custom_users.CustomUser"]["fields"].keys()),
        )

    def test_exclude_and_include_all_apps(self):
        """Excluding all apps and including all apps is the same as not excluding or including anything."""
        default_serializer = Serializer()
        serializer = Serializer(
            exclude_list=[r"auth", "custom_users"],
            include_list=[r"auth", "custom_users"],
        )
        default_serializer.generate_models_list()
        serializer.generate_models_list()
        self.assertEqual(default_serializer.models, serializer.models)
