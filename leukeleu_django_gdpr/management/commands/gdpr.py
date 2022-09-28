import os

import requests

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
        parser.add_argument("--report-pipeline", action="store_true")

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
                "details": f"There are {stats.get(None, 0)} unclassified PII fields.",
                "report_type": "SECURITY",
                "reporter": "django-gdpr",
                "result": "FAILED" if stats.get(None, 0) else "PASSED",
                "data": [
                    {
                        "title": "Unclassified PII fields",
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
        stats = get_pii_stats(save=not options["dry_run"])

        unclassified_fields = stats.get(None, 0)
        self.stdout.write(
            f"PII not set    {unclassified_fields}",
            style_func=self.style.ERROR if unclassified_fields else self.style.SUCCESS,
        )
        self.stdout.write(f"PII True       {stats.get(True, 0)}")
        self.stdout.write(f"PII False      {stats.get(False, 0)}")

        if options["report_pipeline"]:
            self.send_bitbucket_report(stats)

        if options["check"] and unclassified_fields:
            raise CommandError(
                f"There are still {unclassified_fields} unclassified PII fields"
            )
