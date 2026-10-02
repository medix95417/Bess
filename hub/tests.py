import tempfile
from datetime import timedelta
from pathlib import Path
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from hub.admin import save_revision
from hub.models import Citation, Entry, Revision, SiteSettings, Source, validate_pdf

@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class SiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', verbosity=0)
        cls.publisher = get_user_model().objects.create_user('publisher', password='test-only-LongPass!94', is_staff=True)
        cls.publisher.groups.add(Group.objects.get(name='Publishers'))
        cls.contributor = get_user_model().objects.create_user('contributor', password='test-only-LongPass!94', is_staff=True)
        cls.contributor.groups.add(Group.objects.get(name='Contributors'))

    def setUp(self):
        cache.clear()

    def test_public_routes_render_and_cite_sources(self):
        for path in ['/', '/incidents/', '/documents/', '/questions/', '/updates/', '/meetings/', '/search/?q=Warwick', '/healthz/']:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        for entry in Entry.objects.published():
            response = self.client.get(entry.get_absolute_url())
            self.assertEqual(response.status_code, 200, entry.title)
            for citation in entry.citations.all():
                self.assertContains(response, citation.source.url)

    def test_drafts_and_scheduled_content_do_not_leak(self):
        draft = Entry.objects.get(slug='local-packet-review')
        for suffix in ['', '?preview=1']:
            self.assertEqual(self.client.get(draft.get_absolute_url()+suffix).status_code, 404)
        self.assertNotContains(self.client.get('/search/?q=17.6'), 'Local project packet')
        published = Entry.objects.get(slug='mcmicken-2019')
        published.published_at = timezone.now() + timedelta(days=1)
        published.save()
        self.assertEqual(self.client.get(published.get_absolute_url()).status_code, 404)

    def test_staff_preview_requires_permission_and_is_not_cached(self):
        draft = Entry.objects.get(slug='local-packet-review')
        self.client.force_login(self.contributor)
        response = self.client.get(draft.get_absolute_url()+'?preview=1')
        self.assertContains(response, 'EDITOR PREVIEW')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(self.client.get('/editor/').status_code, 200)

    def test_editor_requires_login(self):
        self.assertEqual(self.client.get('/editor/').status_code, 302)

    def test_filters(self):
        response = self.client.get('/incidents/?filter=tesla')
        self.assertContains(response, 'Victorian Big Battery')
        self.assertNotContains(response, 'McMicken: responder')
        response = self.client.get('/incidents/?filter=us')
        self.assertNotContains(response, 'Victorian Big Battery')
        self.assertContains(response, 'Warwick')

    def test_content_is_escaped(self):
        obj=Entry.objects.get(slug='about')
        obj.body='## <script>alert(1)</script>\n\n<img src=x onerror=alert(1)>'
        obj.save()
        response=self.client.get(obj.get_absolute_url())
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;')

    def test_document_validation(self):
        with self.assertRaises(ValidationError):
            validate_pdf(SimpleUploadedFile('fake.pdf', b'<script>bad</script>'))
        with self.assertRaises(ValidationError):
            validate_pdf(SimpleUploadedFile('test.html', b'%PDF-1.4'))
        validate_pdf(SimpleUploadedFile('test.pdf', b'%PDF-1.4\n'))

    def test_private_document_and_public_attachment(self):
        with tempfile.TemporaryDirectory() as temp, override_settings(MEDIA_ROOT=Path(temp)):
            entry=Entry.objects.get(slug='local-packet-review')
            entry.document=SimpleUploadedFile('review.pdf',b'%PDF-1.4\n%%EOF')
            entry.save()
            url=reverse('download',args=[entry.slug])
            self.assertEqual(self.client.get(url).status_code,404)
            self.assertEqual(self.client.get('/private-uploads/'+entry.document.name).status_code,404)
            self.client.force_login(self.publisher)
            response=self.client.get(url+'?preview=1')
            self.assertEqual(response.status_code,200)
            self.assertIn('attachment',response['Content-Disposition'])
            response.close()
            self.client.logout()
            entry.status='published';entry.save()
            response=self.client.get(url)
            self.assertEqual(response.status_code,200)
            response.close()

    def form_data(self, status='draft', verification='editorial'):
        return {'title':'Test new record','slug':'test-new-record','kind':'update','summary':'A test summary.','body':'Text for editorial review.','status':status,'verification':verification,'checked_date':'2026-10-02','order':'0','question_status':'open','citations-TOTAL_FORMS':'1','citations-INITIAL_FORMS':'0','citations-MIN_NUM_FORMS':'0','citations-MAX_NUM_FORMS':'1000','_save':'Save'}

    def test_contributor_can_draft_but_cannot_publish(self):
        self.client.force_login(self.contributor)
        response=self.client.post('/admin/hub/entry/add/', self.form_data('published'))
        self.assertContains(response, 'A publisher must review')
        self.assertFalse(Entry.objects.filter(slug='test-new-record').exists())
        response=self.client.post('/admin/hub/entry/add/', self.form_data())
        self.assertEqual(response.status_code,302)
        entry=Entry.objects.get(slug='test-new-record')
        self.assertEqual(entry.status,'draft')
        self.assertEqual(entry.revisions.count(),1)
        published=Entry.objects.get(slug='about')
        self.assertEqual(self.client.post(reverse('admin:hub_entry_change',args=[published.pk]),self.form_data()).status_code,403)

    def test_publisher_needs_citation_for_documented_claim(self):
        self.client.force_login(self.publisher)
        data=self.form_data('published','documented')
        response=self.client.post('/admin/hub/entry/add/',data)
        self.assertContains(response,'Attach at least one source')
        data.update({'citations-0-source':Source.objects.first().pk,'citations-0-supports':'Supports the test claim.'})
        response=self.client.post('/admin/hub/entry/add/',data)
        self.assertEqual(response.status_code,302)
        entry=Entry.objects.get(slug='test-new-record')
        self.assertEqual(entry.status,'published')
        self.assertEqual(entry.revisions.first().snapshot['citations'][0]['supports'],'Supports the test claim.')

    def test_revision_restore_requires_publisher_and_post(self):
        entry=Entry.objects.get(slug='about')
        old=entry.body
        revision=save_revision(entry,self.publisher)
        entry.body='Changed';entry.save()
        url=reverse('admin:restore-revision',args=[revision.pk])
        self.client.force_login(self.contributor)
        self.assertEqual(self.client.post(url).status_code,403)
        self.client.force_login(self.publisher)
        self.assertEqual(self.client.get(url).status_code,200)
        entry.refresh_from_db();self.assertEqual(entry.body,'Changed')
        self.assertEqual(self.client.post(url).status_code,302)
        entry.refresh_from_db()
        self.assertEqual(entry.body,old)
        self.assertEqual(entry.status,'draft')

    def test_csrf_and_login_throttling(self):
        secure_client=Client(enforce_csrf_checks=True)
        self.assertEqual(secure_client.post('/admin/login/',{'username':'x','password':'bad'}).status_code,403)
        for _ in range(10):
            self.client.post('/admin/login/',{'username':'nonexistent','password':'bad'})
        self.assertEqual(self.client.post('/admin/login/',{'username':'nonexistent','password':'bad'}).status_code,429)

    def test_seed_preserves_editor_changes(self):
        entry=Entry.objects.get(slug='about');entry.body='Editorial change';entry.save()
        count=Entry.objects.count()
        call_command('seed_content',verbosity=0)
        entry.refresh_from_db()
        self.assertEqual(entry.body,'Editorial change')
        self.assertEqual(Entry.objects.count(),count)

class BackupTests(TransactionTestCase):
    def test_backup_contains_database(self):
        import sqlite3
        import tarfile
        with tempfile.TemporaryDirectory() as temp:
            SiteSettings.objects.create(title='Backup verification')
            output=Path(temp)/'backup.tar.gz'
            call_command('backup_site',output=str(output),verbosity=0)
            with tarfile.open(output) as archive:
                self.assertIn('db.sqlite3',archive.getnames())
                archive.extract('db.sqlite3',temp,filter='data')
            with sqlite3.connect(Path(temp)/'db.sqlite3') as db:
                self.assertEqual(db.execute('select title from hub_sitesettings').fetchone()[0],'Backup verification')
