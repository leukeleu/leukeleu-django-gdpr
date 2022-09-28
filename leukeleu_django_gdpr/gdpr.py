import re

from collections import Counter
from inspect import isclass
from itertools import chain
from pathlib import Path

import yaml

from django.apps import AppConfig, apps
from django.conf import settings
from django.db import models
from django.db.models import Field, Model
from django.db.models.fields.related import RelatedField

GDPR_YML_PATH = Path(settings.BASE_DIR) / "gdpr.yml"


def read_data():
    if GDPR_YML_PATH.exists():
        with GDPR_YML_PATH.open() as f:
            data = yaml.safe_load(f)
    else:
        data = {}

    return data


def is_generic_foreign_key(field):
    return (
        getattr(field, "is_relation", False)
        and getattr(field, "related_model", False) is None
    )


class Serializer:
    def __init__(self, exclude_list=None, include_list=None):
        self.models = {}
        self.exclude_list = exclude_list or []
        self.include_list = include_list or []

    def generate_models_list(self):
        self.models = dict(
            chain.from_iterable(
                self.handle_app(app_config)
                for app_config in apps.get_app_configs()
                if self.should_include(app_config)
            )
        )

    def should_include(self, o):
        s = ""
        if isinstance(o, AppConfig):
            s = o.label
        elif isclass(o) and issubclass(o, Model):
            s = o._meta.label
        elif isinstance(o, Field) or is_generic_foreign_key(o):
            s = f"{o.model._meta.label}.{o.name}"

        include = (
            not object_matches_exclude_types(o)
            and not (getattr(o, "auto_created", False))
            and not any(re.fullmatch(pattern, s) for pattern in self.exclude_list)
        ) or any(re.fullmatch(pattern, s) for pattern in self.include_list)

        return include

    def handle_model(self, model):
        return (
            model._meta.label,
            {
                "name": str(model._meta.verbose_name).title(),
                "fields": {
                    field.name: serialize_field(field)
                    for field in model._meta.get_fields()
                    if self.should_include(field)
                },
            },
        )

    def handle_app(self, app_config):
        for model in app_config.get_models():
            if self.should_include(model):
                yield self.handle_model(model)

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
        name = field.verbose_name
        help_text = field.help_text
        if field.is_relation:
            description = f"Relatie naar {field.related_model._meta.verbose_name}"
            required = not field.null
        else:
            description = str(field.description)
            required = not field.blank

    return {
        "name": str(name).title(),
        "description": description,
        "help_text": str(help_text),
        "required": required,
        "pii": None,
    }


EXPLANATION_KEY = "explanation"
DEFAULT_EXCLUDE_TYPES = (
    models.AutoField,
    models.UUIDField,
    models.BooleanField,
    RelatedField,
)
if apps.is_installed("django.contrib.contenttypes"):
    from django.contrib.contenttypes.models import ContentType

    DEFAULT_EXCLUDE_TYPES += (ContentType,)


def object_matches_exclude_types(obj):
    if isclass(obj):
        return issubclass(obj, DEFAULT_EXCLUDE_TYPES)
    else:
        return isinstance(obj, DEFAULT_EXCLUDE_TYPES)


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
        with GDPR_YML_PATH.open("w") as f:
            serializer.save(f)

    return pii_stats(serializer.models)
