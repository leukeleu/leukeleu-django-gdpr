import re

from datetime import datetime
from pathlib import Path

from django.apps import AppConfig, apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.management import BaseCommand
from django.db.models import AutoField, Field, Model

import yaml

from tabulate import tabulate

try:
    from django_cryptography.fields import EncryptedMixin
except ImportError:
    # If django_cryptography is not used in this project, isinstance(field, EncryptedMixin) will now always return False
    class EncryptedMixin:
        pass


class Command(BaseCommand):
    meta_data = {}

    def load_metadata(self):
        input_file = Path("GDPR.yml")
        if not input_file.exists():
            return {}

        with input_file.open() as f:
            self.meta_data = yaml.safe_load(f)

    def should_ignore(self, o):
        s = ""
        if isinstance(o, AppConfig):
            s = o.name
        elif isinstance(o, Model):
            s = f"{o.__module__}.{o.__name__}"
        elif isinstance(o, Field):
            s = f"{o.model.__module__}.{o.model.__name__}.{o.name}"

        return any(re.match(pattern, s) for pattern in self.meta_data.get("ignore", []))

    def handle(self, *args, **options):
        self.load_metadata()

        self.handle_prologue()
        self.handle_text()

        for app_config in apps.get_app_configs():
            if not self.should_ignore(app_config):
                self.handle_app(app_config)

    def handle_prologue(self):
        metadata = {"Date": datetime.now().isoformat(" ")[:19]}
        print("---")
        print(yaml.dump(metadata), end="")
        print("---")
        print()

    def handle_text(self):
        if "text" in self.meta_data:
            print(self.meta_data["text"])
            print()

    def handle_app(self, app_config):
        models = [
            model for model in app_config.get_models() if not self.should_ignore(model)
        ]
        if not models:
            return

        app_name = f"{app_config.verbose_name} [{app_config.name}]"
        print(app_name)
        print("=" * len(app_name))
        print()
        for model in models:
            self.handle_model(model)

        print()

    def handle_model(self, model):
        model_name = f"{model._meta.verbose_name.title()} [{model._meta.model_name}]"
        table = []
        for field in model._meta._get_fields(include_parents=False, reverse=False):
            if not self.should_ignore(field):
                self.handle_field(field, table)
        if table:
            print(model_name)
            print("-" * len(model_name))
            print(
                tabulate(
                    table,
                    tablefmt="github",
                    headers=(
                        "Naam",
                        "Type",
                        "Omschrijving",
                        "Verplicht",
                        "Versleuteld",
                    ),
                )
            )
            print()

    def handle_field(self, field, table):
        if field.is_relation or isinstance(field, AutoField):
            encrypted = "-"
        else:
            encrypted = "Ja" if isinstance(field, EncryptedMixin) else "Nee"
        if field.is_relation:
            if isinstance(field, GenericForeignKey):
                null = True
                description = "Generieke relatie"
            else:
                null = field.null
                description = f"Relatie naar {field.related_model._meta.verbose_name}"
            table.append((field.name, description, "", "" if null else "*", encrypted))
        else:
            required = "" if field.blank else "*"
            table.append(
                (
                    field.verbose_name,
                    field.description,
                    field.help_text,
                    required,
                    encrypted,
                )
            )
