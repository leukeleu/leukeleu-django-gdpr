import os

import requests

from django.core.management import BaseCommand, CommandError

from leukeleu_django_gdpr.gdpr import Serializer, pii_stats, read_data


def get_pii_stats(save=False):
    """
    Determines the PII stats for all models and fields. Takes existing
    data from gdpr.yml into account if it exists. If save is True, the
    data is saved back to gdpr.yml.

    :returns Counter: The PII stats, as a Counter with three keys: None, True
        and False. The None key contains all fields that have not been
        marked as PII or not. The True key contains all fields that have
        been marked as PII. The False key contains all fields that have
        been marked as not PII.
    """
    data = read_data()
    # migration ignore -> exclude: accept both, save as 'exclude'
    exclude_list = data.get("exclude", []) + data.get("ignore", [])
    serializer = Serializer(exclude_list=exclude_list, include_list=data.get("include"))
    serializer.generate_models_list()
    serializer.apply_existing_input_data(data.get("models", {}))
    if save:
        with open("gdpr.yml", "w") as f:
            serializer.save(f)

    return pii_stats(serializer.models)


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
        serializer, stats = get_pii_stats(save=not options["dry_run"])

        unmarked_fields = stats.get(None, 0)
        self.stdout.write(
            f"No PII set     {unmarked_fields}",
            style_func=self.style.ERROR if unmarked_fields else self.style.SUCCESS,
        )
        self.stdout.write(f"PII True       {stats.get(True, 0)}")
        self.stdout.write(f"PII False      {stats.get(False, 0)}")

        if options["report_pipeline"]:
            self.send_bitbucket_report(stats)

        if options["check"] and unmarked_fields:
            raise CommandError(f"There are still {unmarked_fields} unmarked PII fields")
