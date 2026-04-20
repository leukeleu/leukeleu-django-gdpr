import uuid

from importlib import resources
from typing import TYPE_CHECKING, Any, Protocol

from faker import Faker

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.validators import EMPTY_VALUES
from django.db import transaction
from django.db.models import Field, ImageField, Model, Q

from leukeleu_django_gdpr.gdpr import read_data

from . import static

if TYPE_CHECKING:
    from django.db.models.fields.files import ImageFieldFile


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


def anonymize_image_field(obj: Model, field: Field) -> str:
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

    return current_image.path


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
    extra_fieldtype_overrides: dict[str, AnonymizerFunction] | None = None
    extra_qs_overrides = None
    extra_field_overrides: dict[str, AnonymizerFunction] | None = None

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
                            setattr(obj, field_name, value_func(obj=obj, field=field))
                            fields_to_update.add(field_name)

                if fields_to_update:
                    Model.objects.bulk_update(
                        qs,
                        fields_to_update,
                        batch_size=500,
                    )

    def get_fieldtype_overrides(self) -> dict[str, AnonymizerFunction]:
        fieldtype_overrides = {
            "BigIntegerField": lambda obj, field: self.fake.random_int(),
            "BigIntegerField.unique": lambda obj, field: self.fake.unique.random_int(),
            "BooleanField": lambda obj, field: self.fake.boolean(),  # No unique variant
            "CharField": lambda obj, field: self.fake.pystr(),
            "CharField.unique": lambda obj, field: self.fake.unique.pystr(),
            "DateField": lambda obj, field: self.fake.date_this_decade(),
            "DateField.unique": lambda obj, field: self.fake.unique.date_this_decade(),
            "DateTimeField": lambda obj, field: self.fake.date_time_this_decade(),
            "DateTimeField.unique": lambda obj, field: (
                self.fake.unique.date_time_this_decade()
            ),
            "DecimalField": lambda obj, field: self.fake.random_int(),
            "DecimalField.unique": lambda obj, field: self.fake.unique.random_int(),
            "EmailField": lambda obj, field: self.fake.safe_email(),
            "EmailField.unique": lambda obj, field: self.fake.unique.safe_email(),
            "FloatField": lambda obj, field: self.fake.random_int(),
            "FloatField.unique": lambda obj, field: self.fake.unique.random_int(),
            "GenericIPAddressField": lambda obj, field: self.fake.ipv4(),
            "GenericIPAddressField.unique": lambda obj, field: self.fake.unique.ipv4(),
            "ImageField": anonymize_image_field,
            "IntegerField": lambda obj, field: self.fake.random_int(),
            "IntegerField.unique": lambda obj, field: self.fake.unique.random_int(),
            "JSONField": lambda obj, field: self.fake.pydict(
                value_types=["str"]
            ),  # No unique variant
            "PositiveBigIntegerField": lambda obj, field: self.fake.random_int(),
            "PositiveBigIntegerField.unique": lambda obj, field: (
                self.fake.unique.random_int()
            ),
            "PositiveIntegerField": lambda obj, field: self.fake.random_int(),
            "PositiveIntegerField.unique": lambda obj, field: (
                self.fake.unique.random_int()
            ),
            "PositiveSmallIntegerField": lambda obj, field: self.fake.random_int(),
            "PositiveSmallIntegerField.unique": lambda obj, field: (
                self.fake.unique.random_int()
            ),
            "RichTextField": lambda obj, field: self.fake.paragraph(),
            "RichTextField.unique": lambda obj, field: self.fake.unique.paragraph(),
            "SlugField": lambda obj, field: self.fake.pystr(),
            "SlugField.unique": lambda obj, field: self.fake.unique.pystr(),
            "SmallIntegerField": lambda obj, field: self.fake.random_int(),
            "SmallIntegerField.unique": lambda obj, field: (
                self.fake.unique.random_int()
            ),
            "TextField": lambda obj, field: self.fake.paragraph(),
            "TextField.unique": lambda obj, field: self.fake.unique.paragraph(),
            "URLField": lambda obj, field: self.fake.url(),
            "URLField.unique": lambda obj, field: self.fake.unique.url(),
        }

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

    def get_field_overrides(self) -> dict[str, AnonymizerFunction]:
        field_overrides = {
            f"{settings.AUTH_USER_MODEL}.first_name": lambda obj, field: (
                self.fake.first_name
            ),
            f"{settings.AUTH_USER_MODEL}.last_name": lambda obj, field: (
                self.fake.last_name
            ),
        }
        if self.extra_field_overrides is not None:
            field_overrides.update(self.extra_field_overrides)
        return field_overrides
