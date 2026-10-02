import sqlite3
import tarfile
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Back up the SQLite database and uploaded PDFs. Pause editorial writes while this runs.'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True)

    def handle(self, *args, **options):
        output = Path(options['output']).resolve()
        if output.exists():
            raise CommandError('Output already exists. Choose a new backup filename.')
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temp:
            snapshot = Path(temp) / 'db.sqlite3'
            database = str(settings.DATABASES['default']['NAME'])
            with sqlite3.connect(database, uri=database.startswith('file:')) as source, sqlite3.connect(snapshot) as dest:
                source.backup(dest)
            with tarfile.open(output, 'w:gz') as archive:
                archive.add(snapshot, arcname='db.sqlite3')
                if settings.MEDIA_ROOT.exists():
                    archive.add(settings.MEDIA_ROOT, arcname='uploads')
        output.chmod(0o600)
        self.stdout.write(self.style.SUCCESS(f'Backup written: {output}'))
