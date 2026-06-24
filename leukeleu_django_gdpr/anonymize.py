import inspect
import uuid

from collections.abc import Callable, Mapping
from functools import partial
from importlib import resources
from types import MappingProxyType
from typing import Any, Protocol, TypeIs

from faker import Faker

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.validators import EMPTY_VALUES
from django.db import transaction
from django.db.models import Field, ImageField, Model, Q
from django.db.models.fields.files import ImageFieldFile

from leukeleu_django_gdpr.gdpr import read_data

from . import static


def get_models_from_gdpr_yml():
    data = read_data()
    return data["models"]


class AnonymizerFunction(Protocol):
    def __call__(self, obj: Model, field: Field) -> Any:
        """Function to anonymize the value of a field on django model.

        Args:
            obj: the instance of the django model for which the field is anonymized
            field: the field on the django model which is anonymized
        """
        ...


AllowedOverrides = AnonymizerFunction | Callable[[], Any]


def is_anonymizer_function(function: AllowedOverrides) -> TypeIs[AnonymizerFunction]:
    """Check whether override function is a AnonymizerFunction or plain function.

    Returns True if `function` should take the AnonymizerFunction parameters when called
    and false if the function (can and) should take no arguments when called.

    If the function is neither a AnonymizerFunction nor a function which needs no
    arguments a TypeError is raised.
    """

    parameters = inspect.signature(function).parameters

    if set(parameters.keys()) == {"obj", "field"}:
        return True

    non_default_parameters = [
        parameter
        for parameter in parameters.values()
        if parameter.default == inspect.Parameter.empty
    ]

    if not non_default_parameters:
        return False

    raise TypeError(
        "Given function is neither a AnonymizerFunction nor a callable without any "
        "arguments that need to be provided."
    )


def anonymize_image_field(obj: Model, field: Field) -> ImageFieldFile:
    """Function to anonymize image fields on Django models.

    Deletes the original file and generates a new file in the same directory but
    with a anonymized filename.
    """

    if not isinstance(field, ImageField):
        raise TypeError

    current_image: ImageFieldFile = getattr(obj, field.name)

    current_image.delete()

    new_image_bytes = (resources.files(static) / "image.png").read_bytes()
    new_file_name = f"{uuid.uuid4()}.png"
    current_image.save(new_file_name, ContentFile(new_image_bytes))

    return current_image


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
    extra_fieldtype_overrides: Mapping[str, AllowedOverrides] | None = None
    extra_qs_overrides = None
    extra_field_overrides: Mapping[str, AllowedOverrides] | None = None

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
                        if getattr(obj, field_name) in EMPTY_VALUES:
                            continue

                        if is_anonymizer_function(value_func):
                            new_value = value_func(obj=obj, field=field)
                        else:
                            new_value = value_func()

                        setattr(obj, field_name, new_value)
                        fields_to_update.add(field_name)

                if fields_to_update:
                    Model.objects.bulk_update(
                        qs,
                        fields_to_update,
                        batch_size=500,
                    )

    def get_fieldtype_overrides(self) -> Mapping[str, AllowedOverrides]:
        fieldtype_overrides = MappingProxyType(
            {
                "BigIntegerField": self.fake.random_int,
                "BigIntegerField.unique": self.fake.unique.random_int,
                "BooleanField": self.fake.boolean,  # No unique varit
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
                "ImageField": anonymize_image_field,
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
        )

        return fieldtype_overrides | (self.extra_fieldtype_overrides or {})

    def get_qs_overrides(self):
        qs_overrides = {
            settings.AUTH_USER_MODEL: get_user_model()._base_manager.exclude(
                Q(is_superuser=True) | Q(is_staff=True)
            ),
        }
        if self.extra_qs_overrides is not None:
            qs_overrides.update(self.extra_qs_overrides)
        return qs_overrides

    def get_field_overrides(self) -> Mapping[str, AllowedOverrides]:
        field_overrides = MappingProxyType(
            {
                f"{settings.AUTH_USER_MODEL}.first_name": self.fake.first_name,
                f"{settings.AUTH_USER_MODEL}.last_name": self.fake.last_name,
            }
        )
        return field_overrides | (self.extra_field_overrides or {})
