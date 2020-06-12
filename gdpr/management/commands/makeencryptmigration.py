import os

from django.apps import apps
from django.core.management import BaseCommand, CommandError
from django.db.migrations import Migration
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState

from ...writer import EncryptMigrationWriter


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "model",
            help="The model to create the migration for, as app_label.ModelName",
        )
        parser.add_argument(
            "--fields",
            metavar="field",
            nargs="+",
            help="Encrypt these specific fields. Leave blank to list all model fields, "
            "commented.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Just show what migrations would be made; don't actually write them.",
        )

    def handle(self, model, *args, **options):
        self.verbosity = options["verbosity"]
        self.dry_run = options["dry_run"]
        self.fields = options["fields"]

        if "." not in model:
            raise CommandError("model argument must be like app_label.ModelClass")

        Model = apps.get_model(model)
        app_label = Model._meta.app_label

        migration_name = f"encrypt_{Model._meta.object_name}"

        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(
            loader.project_state(), ProjectState.from_apps(apps),
        )

        changes = {app_label: [Migration("custom", app_label)]}
        changes = autodetector.arrange_for_graph(
            changes=changes, graph=loader.graph, migration_name=migration_name
        )

        migration = changes[app_label][0]  # What if not?
        writer = EncryptMigrationWriter(Model, self.fields, migration)

        if self.verbosity >= 1:
            # Display a relative path if it's below the current working
            # directory, or an absolute path otherwise.
            try:
                migration_string = os.path.relpath(writer.path)
            except ValueError:
                migration_string = writer.path
            if migration_string.startswith(".."):
                migration_string = writer.path
            self.stdout.write("  %s\n" % (self.style.MIGRATE_LABEL(migration_string),))
            for field in writer.encryptable_fields():
                self.stdout.write(
                    "    - Encrypt field %s on %s\n"
                    % (field.name, field.model._meta.object_name)
                )
        if not self.dry_run:
            # Write the migrations file to the disk.
            migration_string = writer.as_string()
            with open(writer.path, "w", encoding="utf-8") as fh:
                fh.write(migration_string)
        elif self.verbosity == 3:
            # Alternatively, makemigrations --dry-run --verbosity 3
            # will output the migrations to stdout rather than saving
            # the file to the disk.
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "Full migrations file '%s':" % writer.filename
                )
                + "\n"
            )
            self.stdout.write("%s\n" % writer.as_string())
