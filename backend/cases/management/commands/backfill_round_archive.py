from django.core.management.base import BaseCommand
from cases.archive import preserve, section
from cases.models import Game, RoundArchive


class Command(BaseCommand):
    help = "Index existing fictional virtual rounds without copying player identifiers or scanner data."

    def handle(self, *args, **options):
        before=RoundArchive.objects.count()
        for game in Game.objects.order_by('created').iterator():
            if section(game.case):
                preserve(game.case,backfill=True)
        self.stdout.write(self.style.SUCCESS(f'Archived {RoundArchive.objects.count()-before} existing virtual rounds.'))
