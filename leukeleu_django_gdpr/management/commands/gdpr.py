from django.core.management import BaseCommand, CommandError

from leukeleu_django_gdpr.gdpr import get_pii_stats


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit with a non-zero status code if PII classification is missing for one or more model fields.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't save the new data to the file.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Checking...")
        stats = get_pii_stats(save=not options["dry_run"])

        unclassified_fields = stats.get(None, 0)
        self.stdout.write(
            f"PII not set    {unclassified_fields}",
            style_func=self.style.ERROR if unclassified_fields else self.style.SUCCESS,
        )
        self.stdout.write(f"PII True       {stats.get(True, 0)}")
        self.stdout.write(f"PII False      {stats.get(False, 0)}")

        if options["check"] and unclassified_fields:
            raise CommandError(
                f"There are still {unclassified_fields} unclassified PII fields"
            )
