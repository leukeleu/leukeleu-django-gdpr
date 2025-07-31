from functools import partial

from faker import Faker

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import EMPTY_VALUES
from django.db import transaction
from django.db.models import Q

from leukeleu_django_gdpr.gdpr import read_data


def get_models_from_gdpr_yml():
    data = read_data()
    return data["models"]


class BaseAnonymizer:
    """
    Base class for anonymizing data.

    By default:
        - superusers and staff users are excluded from anonymization
        - the user's first_name and last_name are filled with fake first/last names

    Options:
        excluded_fields: List of fields to exclude from anonymization
            example: ["app.Model.field"]

        extra_fieldtype_overrides: Dict of field type overrides
            example: {"CustomPhoneNumberField": fake.phone_number}

        extra_qs_overrides: Dict of queryset overrides
            example: {"app.Model": Model.objects.exclude(some_field=...)}

        extra_field_overrides: Dict of field overrides
            example: {"app.Model.field": fake.word}
    """

    excluded_fields = []
    extra_fieldtype_overrides = None
    extra_qs_overrides = None
    extra_field_overrides = None

    def __init__(self):
        self.fake = Faker(["nl-NL"])

    def anonymize(self):
        fieldtype_overrides = self.get_fieldtype_overrides()
        qs_overrides = self.get_qs_overrides()
        field_overrides = self.get_field_overrides()

        with transaction.atomic():
            models = get_models_from_gdpr_yml()
            for model_name, model_data in models.items():
                print(f"Currently anonymizing: {model_name}")  # noqa: T201

                Model = apps.get_model(model_name)

                # Calling .all() makes sure we are always dealing with the latest data
                qs = qs_overrides.get(model_name, Model._base_manager).all()

                # Collect fields that actually need to be updated and skip updating
                # entirely if the set is empty
                fields_to_update = set()

                for field_name, field_data in model_data["fields"].items():
                    field_path = f"{model_name}.{field_name}"
                    if not field_data["pii"] or field_path in self.excluded_fields:
                        # Leave non PII and ignored fields alone
                        continue

                    field = Model._meta.get_field(field_name)

                    field_type = type(field).__name__
                    if field.unique:
                        field_type += ".unique"

                    try:
                        value_func = field_overrides.get(
                            field_path,
                            fieldtype_overrides[field_type],
                        )
                    except KeyError:
                        raise ImproperlyConfigured(
                            f"Unknown field type: '{field_type}'"
                        ) from None

                    for obj in qs:
                        if getattr(obj, field_name) not in EMPTY_VALUES:
                            setattr(obj, field_name, value_func())
                            fields_to_update.add(field_name)

                if fields_to_update:
                    Model.objects.bulk_update(
                        qs,
                        fields_to_update,
                        batch_size=500,
                    )

    def get_fieldtype_overrides(self):
        fieldtype_overrides = {
            "BigIntegerField": self.fake.random_int,
            "BigIntegerField.unique": self.fake.unique.random_int,
            "BooleanField": self.fake.boolean,  # No unique variant
            "CharField": self.fake.pystr,
            "CharField.unique": self.fake.unique.pystr,
            "DateField": self.fake.date_this_decade,
            "DateField.unique": self.fake.unique.date_this_decade,
            "DateTimeField": self.fake.date_time_this_decade,
            "DateTimeField.unique": self.fake.unique.date_time_this_decade,
            "DecimalField": self.fake.random_int,
            "DecimalField.unique": self.fake.unique.random_int,
            "EmailField": self.fake.safe_email,
            "EmailField.unique": self.fake.unique.safe_email,
            "FloatField": self.fake.random_int,
            "FloatField.unique": self.fake.unique.random_int,
            "GenericIPAddressField": self.fake.ipv4,
            "GenericIPAddressField.unique": self.fake.unique.ipv4,
            "IntegerField": self.fake.random_int,
            "IntegerField.unique": self.fake.unique.random_int,
            "JSONField": partial(
                self.fake.pydict,
                value_types=["str"],
            ),  # No unique variant
            "PositiveBigIntegerField": self.fake.random_int,
            "PositiveBigIntegerField.unique": self.fake.unique.random_int,
            "PositiveIntegerField": self.fake.random_int,
            "PositiveIntegerField.unique": self.fake.unique.random_int,
            "PositiveSmallIntegerField": self.fake.random_int,
            "PositiveSmallIntegerField.unique": self.fake.unique.random_int,
            "RichTextField": self.fake.paragraph,
            "RichTextField.unique": self.fake.unique.paragraph,
            "SlugField": self.fake.pystr,
            "SlugField.unique": self.fake.unique.pystr,
            "SmallIntegerField": self.fake.random_int,
            "SmallIntegerField.unique": self.fake.unique.random_int,
            "TextField": self.fake.paragraph,
            "TextField.unique": self.fake.unique.paragraph,
            "URLField": self.fake.url,
            "URLField.unique": self.fake.unique.url,
        }

        if self.extra_fieldtype_overrides is not None:
            fieldtype_overrides.update(self.extra_fieldtype_overrides)
        return fieldtype_overrides

    def get_qs_overrides(self):
        qs_overrides = {
            settings.AUTH_USER_MODEL: get_user_model()._base_manager.exclude(
                Q(is_superuser=True) | Q(is_staff=True)
            ),
        }
        if self.extra_qs_overrides is not None:
            qs_overrides.update(self.extra_qs_overrides)
        return qs_overrides

    def get_field_overrides(self):
        field_overrides = {
            f"{settings.AUTH_USER_MODEL}.first_name": self.fake.first_name,
            f"{settings.AUTH_USER_MODEL}.last_name": self.fake.last_name,
        }
        if self.extra_field_overrides is not None:
            field_overrides.update(self.extra_field_overrides)
        return field_overrides
