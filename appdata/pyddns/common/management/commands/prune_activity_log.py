import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from common.models import Activity_log


class Command(BaseCommand):
    help = (
        "Delete Activity_log rows older than N weeks. "
        "Defaults to ACTIVITY_LOG_RETENTION_WEEKS (or 10). "
        "Pass --weeks 0 to disable (no rows deleted)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--weeks",
            type=int,
            default=None,
            help="Retention window in weeks. Overrides ACTIVITY_LOG_RETENTION_WEEKS.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without modifying the DB.",
        )

    def handle(self, *args, **options):
        weeks = options["weeks"]
        if weeks is None:
            weeks = int(os.environ.get("ACTIVITY_LOG_RETENTION_WEEKS", "10"))

        if weeks <= 0:
            self.stdout.write("Retention disabled (weeks=%d); nothing to do." % weeks)
            return

        cutoff = timezone.now() - timedelta(weeks=weeks)
        qs = Activity_log.objects.filter(date__lt=cutoff)
        count = qs.count()

        if options["dry_run"]:
            self.stdout.write(
                "Would delete %d Activity_log row(s) older than %s (%d weeks)."
                % (count, cutoff.isoformat(), weeks)
            )
            return

        deleted, _ = qs.delete()
        self.stdout.write(
            "Deleted %d Activity_log row(s) older than %s (%d weeks)."
            % (deleted, cutoff.isoformat(), weeks)
        )
