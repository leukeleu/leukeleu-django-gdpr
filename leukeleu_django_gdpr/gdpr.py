import re

from collections import Counter
from itertools import chain
from pathlib import Path

import yaml

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models.fields.related import RelatedField
from django.utils.safestring import SafeString


def get_gdpr_yml_path():
    if hasattr(settings, "DJANGO_GDPR_YML_DIR"):
        return Path(settings.DJANGO_GDPR_YML_DIR) / "gdpr.yml"
    else:
        return Path(settings.BASE_DIR) / "gdpr.yml"


def read_data():
    path = get_gdpr_yml_path()
    if path.exists():
        with path.open() as f:
            data = yaml.safe_load(f)
    else:
        data = {}

    return data


def is_generic_foreign_key(field):
    return (
        getattr(field, "is_relation", False)
        and getattr(field, "related_model", False) is None
    )


def _str(s):
    """
    Call str on an object and return the result,
    if the object is a SafeString make it a normal string.
    """
    s = str(s)  # Convert lazy strings to (safe)strings
    if isinstance(s, SafeString):
        # Adding a non-safe str to a SafeString will return s str
        # (not a SafeString) this is the only way to undo mark_safe
        s = s + ""
    return s


class Serializer:
    def __init__(self, exclude_list=None, include_list=None):
        self.models = {}
        self.exclude_list = exclude_list or []
        self.include_list = include_list or []

    def generate_models_list(self):
        self.models = dict(
            chain.from_iterable(
                self.handle_app(app_config) for app_config in apps.get_app_configs()
            )
        )

    def should_include_field(self, model, field):
        app_label = model._meta.app_label
        model_name = f"{app_label}.{model.__name__}"
        field_name = f"{model_name}.{field.name}"

        field_must_be_included = any(
            re.fullmatch(pattern, field_name) for pattern in self.include_list
        )

        if not field_must_be_included and (
            isinstance(field, DEFAULT_EXCLUDE_FIELDS) or field.auto_created
        ):
            # Exclude fields that are not relevant for GDPR, unless they are explicitly included
            return False

        if field_must_be_included or any(
            re.fullmatch(pattern, model_name) or re.fullmatch(pattern, app_label)
            for pattern in self.include_list
        ):
            # The app, model or field is explicitly included, include it
            return True

        if model._meta.app_config.name in DEFAULT_EXCLUDED_APPS:
            # If the app is in the default excluded apps, exclude it
            return False

        # Check if the app, model or field is explicitly excluded
        return not any(
            re.fullmatch(pattern, field_name)
            or re.fullmatch(pattern, model_name)
            or re.fullmatch(pattern, app_label)
            for pattern in self.exclude_list
        )

    def handle_model(self, model):
        return (
            model._meta.label,
            {
                "name": _str(model._meta.verbose_name).title(),
                "fields": {
                    field.name: serialize_field(field)
                    for field in model._meta.get_fields()
                    if self.should_include_field(model, field)
                },
            },
        )

    def handle_app(self, app_config):
        for model in app_config.get_models():
            if model._meta.proxy:
                continue  # Skip proxy models
            model_label, model_dict = self.handle_model(model)
            if model_dict["fields"]:
                yield model_label, model_dict

    def apply_existing_input_data(self, input_data):
        for model_label in self.models:
            for field_label in self.models[model_label]["fields"]:
                self.models[model_label]["fields"][field_label].update(
                    get_manual_input_for_field(input_data, model_label, field_label)
                )

    def save(self, stream):
        yaml.dump(
            {
                "exclude": self.exclude_list,
                "include": self.include_list,
                "models": self.models,
            },
            stream=stream,
            sort_keys=False,
            indent=2,
        )


def serialize_field(field):
    if is_generic_foreign_key(field):
        required = False
        name = field.name
        description = "Generieke relatie"
        help_text = None
    else:
        name = getattr(field, "verbose_name", None) or getattr(field, "name", None)
        help_text = getattr(field, "help_text", None)
        if field.is_relation:
            description = f"Relatie naar {field.related_model._meta.verbose_name}"
            required = not field.null
        else:
            description = field.description
            required = not field.blank

    return {
        "name": _str(name).title(),
        "description": _str(description),
        "help_text": _str(help_text),
        "required": required,
        "pii": None,
    }


EXPLANATION_KEY = "explanation"
DEFAULT_EXCLUDED_APPS = (
    "django.contrib.admin",
    "django.contrib.contenttypes",
)
DEFAULT_EXCLUDE_FIELDS = (
    models.AutoField,
    models.UUIDField,
    models.BooleanField,
    RelatedField,
)


def pii_stats(models):
    counter = Counter()
    for model in models.values():
        for field in model["fields"].values():
            counter[field["pii"]] += 1

    return counter


def get_manual_input_for_field(data, model_label, field_label):
    model = data.get(model_label)
    if model:
        field = model["fields"].get(field_label, {})
        input_data = {
            "pii": field.get("pii", None),
        }
        if field.get(EXPLANATION_KEY):
            input_data[EXPLANATION_KEY] = field[EXPLANATION_KEY]
        return input_data
    return {}


def get_pii_stats(save=False):
    """
    Determines the PII stats for all models. Any data from an existing
    gdpr.yml is taken into account. If save is True, the data is saved
    to gdpr.yml.

    :returns A Counter with three keys:
        * None: all fields that have not been classified
        * True: all fields that have been classified as PII
        * False: all fields that have been classified as non-PII.
    """
    data = read_data()
    # Previous versions used "ignore", migrate to "exclude"
    exclude_list = data.get("exclude", data.get("ignore", []))
    serializer = Serializer(exclude_list=exclude_list, include_list=data.get("include"))
    serializer.generate_models_list()
    serializer.apply_existing_input_data(data.get("models", {}))
    if save:
        with get_gdpr_yml_path().open("w") as f:
            serializer.save(f)

    return pii_stats(serializer.models)
