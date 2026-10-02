import uuid
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

def document_path(instance, filename):
    return f'documents/{uuid.uuid4().hex}.pdf'

def validate_pdf(file):
    if file.size > 20 * 1024 * 1024:
        raise ValidationError('PDFs must be 20 MB or smaller.')
    if Path(file.name).suffix.lower() != '.pdf':
        raise ValidationError('Upload a PDF. Link to other formats using a source URL.')
    file.open('rb')
    header = file.read(5)
    file.seek(0)
    if header != b'%PDF-':
        raise ValidationError('The file does not appear to be a PDF.')

web_url = URLValidator(schemes=['http', 'https'])

class Source(models.Model):
    title = models.CharField(max_length=240)
    publisher = models.CharField(max_length=160)
    url = models.URLField(max_length=1000, validators=[web_url])
    published_date = models.DateField(null=True, blank=True)
    checked_date = models.DateField(default=timezone.localdate)
    source_type = models.CharField(max_length=24, choices=[('agency', 'Government / agency'), ('research', 'Research organization'), ('operator', 'Operator / developer'), ('news', 'News report'), ('community', 'Community analysis')], default='agency')
    notes = models.TextField(blank=True, help_text='Public source context, limitations, or corrections.')

    class Meta:
        ordering = ['publisher', 'title']

    def __str__(self):
        return f'{self.publisher}: {self.title}'

class EntryQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status='published', published_at__lte=timezone.now())

class Entry(models.Model):
    KINDS = [('page', 'Guide / project page'), ('incident', 'Incident'), ('document', 'Document / resource'), ('question', 'Community question'), ('update', 'Update'), ('meeting', 'Meeting')]
    VERIFICATIONS = [('documented', 'Documented'), ('statement', 'Attributed statement'), ('estimate', 'Estimate'), ('review', 'Awaiting confirmation'), ('editorial', 'Community question / editorial')]
    title = models.CharField(max_length=240)
    slug = models.SlugField(max_length=240, unique=True)
    kind = models.CharField(max_length=20, choices=KINDS, default='update')
    summary = models.TextField(max_length=650, help_text='A short, plain-language introduction.')
    body = models.TextField(help_text='Plain text. Use a blank line between paragraphs and ## for section headings. HTML is escaped.')
    status = models.CharField(max_length=20, choices=[('draft', 'Draft'), ('review', 'Ready for review'), ('published', 'Published')], default='draft')
    verification = models.CharField(max_length=20, choices=VERIFICATIONS, default='review')
    checked_date = models.DateField(null=True, blank=True, help_text='When the cited evidence was actually checked, not the last edit date.')
    published_at = models.DateTimeField(null=True, blank=True, help_text='A future date schedules publication. Set automatically on first publication if blank.')
    updated_at = models.DateTimeField(auto_now=True)
    change_note = models.CharField(max_length=500, blank=True, help_text='Public explanation of a correction or material update.')
    featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    document = models.FileField(upload_to=document_path, validators=[validate_pdf], blank=True, help_text='Optional PDF, up to 20 MB. Downloads are attachments, and drafts remain private.')
    # Incident and meeting fields. Leave unknown facts blank.
    event_date = models.DateField(null=True, blank=True)
    event_time = models.TimeField(null=True, blank=True, help_text='Meetings: America/New_York local time.')
    location = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=80, blank=True)
    manufacturer = models.CharField(max_length=160, blank=True)
    chemistry = models.CharField(max_length=120, blank=True)
    outcome = models.CharField(max_length=30, blank=True, choices=[('fire', 'Fire reported'), ('explosion', 'Explosion reported'), ('other', 'Other failure')])
    impact = models.TextField(blank=True, help_text='Documented injuries, evacuations, closures, or monitoring findings. Include limits.')
    comparison = models.TextField(blank=True, help_text='What this event can and cannot tell us about Woodlawn.')
    latitude = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    question_status = models.CharField(max_length=24, choices=[('open', 'Open question'), ('requested', 'Response requested'), ('partial', 'Partial response'), ('answered', 'Response available')], default='open')
    response = models.TextField(blank=True, help_text='Attribute the response and cite its source. Do not describe a request as sent unless it was sent.')
    response_by = models.CharField(max_length=160, blank=True)
    objects = EntryQuerySet.as_manager()

    class Meta:
        ordering = ['order', '-published_at', 'title']
        permissions = [('publish_entry', 'Can publish and edit published entries')]
        verbose_name_plural = 'Entries'

    def __str__(self):
        return self.title

    def clean(self):
        errors = {}
        if (self.latitude is None) != (self.longitude is None):
            errors['latitude'] = 'Enter both latitude and longitude, or leave both blank.'
        if self.status == 'published' and not self.checked_date:
            errors['checked_date'] = 'Record an evidence review date before publishing.'
        if self.kind in ('incident', 'meeting') and self.status == 'published' and not self.event_date:
            errors['event_date'] = 'A published incident or meeting needs a date.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('entry', kwargs={'slug': self.slug})

class Citation(models.Model):
    entry = models.ForeignKey(Entry, related_name='citations', on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    supports = models.CharField(max_length=350, help_text='Which statement this supports; include page/section when useful.')

    def __str__(self):
        return self.supports

class Revision(models.Model):
    entry = models.ForeignKey(Entry, related_name='revisions', on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)
    saved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    snapshot = models.JSONField()
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-saved_at']

    def __str__(self):
        return f'{self.entry.title} — {self.saved_at:%Y-%m-%d %H:%M}'

class SiteSettings(models.Model):
    title = models.CharField(max_length=180, default='Woodlawn Energy Storage')
    subtitle = models.CharField(max_length=180, default='Community Information Center')
    introduction = models.TextField(default='Understand the proposal. Read the evidence. Follow the questions that matter to Woodlawn.')
    operator_name = models.CharField(max_length=180, blank=True, help_text='Who operates this website. Complete before public launch.')
    contact_email = models.EmailField(blank=True)
    project_status = models.CharField(max_length=180, default='Current permit status awaiting verification')
    project_status_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Site settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Website name, contact, and project status'
