import os
import re

from collections import Counter
from inspect import isclass
from itertools import chain
from pathlib import Path

import requests
import yaml

from django.apps import AppConfig, apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand, CommandError
from django.db import models
from django.db.models import Field, Model
from django.db.models.fields.related import RelatedField

EXPLANATION_KEY = "explanation"
DEFAULT_EXCLUDE_TYPES = (
    models.AutoField,
    models.UUIDField,
    models.BooleanField,
    RelatedField,
    ContentType,
)


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


def serialize_field(field):
    if isinstance(field, GenericForeignKey):
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
        elif isinstance(o, (Field, GenericForeignKey)):
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


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit with non-zero exit code if there are any unmarked pii fields",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't save the new data to the file.",
        )
        parser.add_argument("--report-pipeline", action="store_true")

    def read_data(self):
        gdpr_file = Path("gdpr.yml")
        if gdpr_file.exists():
            with gdpr_file.open() as f:
                data = yaml.safe_load(f)
        else:
            data = {}

        return data

    def send_bitbucket_report(self, stats):
        proxy = "http://localhost:29418"
        repo_owner = os.environ["BITBUCKET_REPO_OWNER"]
        repo_slug = os.environ["BITBUCKET_REPO_SLUG"]
        commit = os.environ["BITBUCKET_COMMIT"]
        url = (
            f"http://api.bitbucket.org/2.0/repositories/"
            f"{repo_owner}/{repo_slug}/commit/{commit}/reports/gdpr-report-001"
        )
        requests.put(
            url,
            proxies={"https": proxy, "http": proxy},
            json={
                "title": "GDPR scan report",
                "details": f"There are {stats.get(None, 0)} unmarked PII fields.",
                "report_type": "SECURITY",
                "reporter": "django-gdpr",
                "result": "FAILED" if stats.get(None, 0) else "PASSED",
                "data": [
                    {
                        "title": "Unmarked PII fields",
                        "type": "NUMBER",
                        "value": stats.get(None, 0),
                    },
                    {
                        "title": "PII: True fields",
                        "type": "NUMBER",
                        "value": stats.get(True, 0),
                    },
                    {
                        "title": "PII: False fields",
                        "type": "NUMBER",
                        "value": stats.get(False, 0),
                    },
                ],
            },
        ).raise_for_status()

    def handle(self, *args, **options):
        self.stdout.write("Checking...")
        data = self.read_data()

        # migration ignore -> exclude: accept both, save as 'exclude'
        exclude_list = data.get("exclude", []) + data.get("ignore", [])

        serializer = Serializer(
            exclude_list=exclude_list, include_list=data.get("include")
        )
        serializer.generate_models_list()
        serializer.apply_existing_input_data(data.get("models", {}))
        stats = pii_stats(serializer.models)

        unmarked_fields = stats.get(None, 0)
        self.stdout.write(
            f"No PII set     {unmarked_fields}",
            style_func=self.style.ERROR if unmarked_fields else self.style.SUCCESS,
        )
        self.stdout.write(f"PII True       {stats.get(True, 0)}")
        self.stdout.write(f"PII False      {stats.get(False, 0)}")

        if not options["dry_run"]:
            with open("gdpr.yml", "w") as f:
                serializer.save(f)

        if options["report_pipeline"]:
            self.send_bitbucket_report(stats)

        if options["check"] and unmarked_fields:
            raise CommandError(f"There are still {unmarked_fields} unmarked PII fields")
