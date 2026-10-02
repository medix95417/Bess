import json
from django import forms
from django.contrib import admin, messages
from django.core import serializers
from django.core.exceptions import PermissionDenied, ValidationError
from django.forms.models import BaseInlineFormSet
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from .models import Citation, Entry, Revision, SiteSettings, Source

admin.site.site_header = 'Woodlawn • Editorial desk'
admin.site.site_title = 'Woodlawn editor'
admin.site.index_title = 'Manage the information center'

class CitationFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        present = any(f.cleaned_data.get('source') and not f.cleaned_data.get('DELETE') for f in self.forms)
        if self.instance.status == 'published' and self.instance.verification in ('documented', 'statement', 'estimate') and not present:
            raise ValidationError('Attach at least one source before publishing a documented fact, attributed statement, or estimate.')

class CitationInline(admin.TabularInline):
    model = Citation
    formset = CitationFormSet
    extra = 1
    autocomplete_fields = ['source']

def save_revision(entry, user, note=None):
    fields = json.loads(serializers.serialize('json', [entry]))[0]['fields']
    citations = list(entry.citations.values('source_id', 'supports'))
    return Revision.objects.create(entry=entry, saved_by=user, snapshot={'fields': fields, 'citations': citations}, note=note if note is not None else entry.change_note)

@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ['title', 'kind', 'status', 'verification', 'checked_date', 'updated_at', 'preview_link']
    list_filter = ['kind', 'status', 'verification', 'question_status']
    search_fields = ['title', 'body', 'location', 'summary']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [CitationInline]
    readonly_fields = ['updated_at', 'preview_link']
    fieldsets = [
        ('Content', {'fields': ('kind', 'title', 'slug', 'summary', 'body')}),
        ('Review & publishing', {'fields': ('status', 'verification', 'checked_date', 'published_at', 'change_note', 'featured', 'order', 'updated_at', 'preview_link')}),
        ('PDF document', {'fields': ('document',), 'classes': ('collapse',)}),
        ('Incident / meeting details', {'fields': ('event_date', 'event_time', 'location', 'country', 'manufacturer', 'chemistry', 'outcome', 'impact', 'comparison', 'latitude', 'longitude'), 'classes': ('collapse',)}),
        ('Question & response', {'fields': ('question_status', 'response', 'response_by'), 'classes': ('collapse',)}),
    ]

    def get_form(self, request, obj=None, **kwargs):
        base = super().get_form(request, obj, **kwargs)
        class AuthorizedForm(base):
            def clean(self):
                data = super().clean()
                if data.get('status') == 'published' and not request.user.has_perm('hub.publish_entry'):
                    self.add_error('status', 'A publisher must review and publish this entry.')
                return data
        return AuthorizedForm

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'published' and not request.user.has_perm('hub.publish_entry'):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        if obj.status == 'published' and not request.user.has_perm('hub.publish_entry'):
            raise PermissionDenied
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        save_revision(form.instance, request.user)

    @admin.display(description='Preview')
    def preview_link(self, obj):
        if obj.pk:
            return format_html('<a href="{}?preview=1">Preview page</a>', obj.get_absolute_url())
        return 'Save a draft to preview it.'

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'publisher', 'source_type', 'checked_date']
    list_filter = ['source_type', 'publisher']
    search_fields = ['title', 'publisher', 'url']

@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ['entry', 'saved_at', 'saved_by', 'note', 'restore_link']
    readonly_fields = ['entry', 'saved_at', 'saved_by', 'snapshot', 'note', 'restore_link']
    search_fields = ['entry__title', 'note']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Recovery')
    def restore_link(self, obj):
        return format_html('<a href="{}">Restore as draft</a>', reverse('admin:restore-revision', args=[obj.pk]))

    def get_urls(self):
        return [path('<int:pk>/restore/', self.admin_site.admin_view(self.restore_view), name='restore-revision')] + super().get_urls()

    def restore_view(self, request, pk):
        if not (request.user.has_perm('hub.publish_entry') and request.user.has_perm('hub.change_entry')):
            raise PermissionDenied
        revision = get_object_or_404(Revision, pk=pk)
        if request.method == 'POST':
            from django.db import transaction
            with transaction.atomic():
                entry = Entry.objects.select_for_update().get(pk=revision.entry_id)
                save_revision(entry, request.user, 'Snapshot before restoring an earlier revision')
                for name, value in revision.snapshot['fields'].items():
                    if name not in ('updated_at', 'status', 'published_at'):
                        field = Entry._meta.get_field(name)
                        setattr(entry, name, field.to_python(value))
                entry.status = 'draft'
                entry.published_at = None
                entry.change_note = f'Restored revision {revision.pk} as draft for review.'
                entry.save()
                entry.citations.all().delete()
                for citation in revision.snapshot['citations']:
                    Citation.objects.create(entry=entry, **citation)
                save_revision(entry, request.user)
            messages.success(request, 'Restored as draft. Review and publish when ready.')
            return redirect('admin:hub_entry_change', entry.pk)
        return render(request, 'admin/restore.html', {**self.admin_site.each_context(request), 'revision': revision, 'title': 'Restore an earlier version'})

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
