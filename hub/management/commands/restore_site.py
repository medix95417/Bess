import tarfile
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Restore into an EMPTY data directory. Run with the web service stopped.'

    def add_arguments(self, parser):
        parser.add_argument('archive')

    def handle(self, *args, **options):
        target = settings.DATA_DIR.resolve()
        if (target / 'db.sqlite3').exists() or (target / 'uploads').exists():
            raise CommandError('Destination already contains data. Restore only into an empty volume.')
        with tarfile.open(options['archive'], 'r:gz') as archive:
            for member in archive.getmembers():
                resolved = (target / member.name).resolve()
                if not resolved.is_relative_to(target) or member.issym() or member.islnk() or member.isdev():
                    raise CommandError('Archive contains an unsafe path or unsupported member.')
                if member.name not in ('db.sqlite3', 'uploads') and not member.name.startswith('uploads/'):
                    raise CommandError('Unexpected file in backup.')
            archive.extractall(target, filter='data')
        self.stdout.write(self.style.SUCCESS('Restored. Start the service to apply any pending migrations.'))
