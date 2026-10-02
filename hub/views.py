from pathlib import Path
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from .models import Entry

SECTIONS = {
    'incidents': ('incident', 'Incidents & lessons learned', 'A selected, sourced case library. Each event has its own circumstances; these records do not establish the likelihood of an incident in Woodlawn.'),
    'documents': ('document', 'The public record', 'Read the source material behind the discussion. Search reports, agency resources, and project documents.'),
    'questions': ('question', 'Questions worth answering', 'Specific questions for the developer and reviewing agencies, with space for attributed, documented responses.'),
    'updates': ('update', 'Latest updates', 'Dated developments, new evidence, and corrections. Earlier updates remain part of the record.'),
    'meetings': ('meeting', 'Meetings & participation', 'Published meeting dates, agendas, and summaries. Times are shown in New York local time.'),
}

def home(request):
    qs = Entry.objects.published()
    return render(request, 'hub/home.html', {'title': 'Understand the Woodlawn proposal', 'updates': qs.filter(kind='update').order_by('-published_at')[:3], 'questions': qs.filter(kind='question')[:3], 'incidents': qs.filter(kind='incident').order_by('-event_date')[:3], 'incident_count': qs.filter(kind='incident').count(), 'document_count': qs.filter(kind='document').count(), 'question_count': qs.filter(kind='question').exclude(question_status='answered').count()})

def listing(request, section):
    if section not in SECTIONS:
        raise Http404
    kind, title, description = SECTIONS[section]
    qs = Entry.objects.published().filter(kind=kind)
    q = request.GET.get('q', '').strip()[:200]
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q) | Q(location__icontains=q) | Q(manufacturer__icontains=q))
    selection = request.GET.get('filter', '')
    if kind == 'incident':
        if selection == 'us':
            qs = qs.filter(country='United States')
        elif selection == 'tesla':
            qs = qs.filter(manufacturer__icontains='Tesla')
        qs = qs.order_by('-event_date')
    elif kind == 'question' and selection == 'open':
        qs = qs.exclude(question_status='answered')
    elif kind == 'question' and selection == 'answered':
        qs = qs.filter(question_status='answered')
    elif kind == 'meeting':
        qs = qs.order_by('-event_date')
    else:
        qs = qs.order_by('-published_at')
    points = [{'title': e.title, 'url': e.get_absolute_url(), 'latitude': e.latitude, 'longitude': e.longitude, 'outcome': e.get_outcome_display(), 'date': e.event_date.isoformat() if e.event_date else ''} for e in qs if e.latitude is not None and e.longitude is not None] if kind == 'incident' else []
    return render(request, 'hub/listing.html', {'title': title, 'description': description, 'kind': kind, 'section': section, 'q': q, 'selection': selection, 'page_obj': Paginator(qs, 12).get_page(request.GET.get('page')), 'points': points})

def visible_entries(request):
    if request.GET.get('preview') == '1' and request.user.is_staff and request.user.has_perm('hub.view_entry'):
        return Entry.objects.all()
    return Entry.objects.published()

def entry_detail(request, slug):
    entry = get_object_or_404(visible_entries(request).prefetch_related('citations__source'), slug=slug)
    is_preview = request.GET.get('preview') == '1' and request.user.is_staff and request.user.has_perm('hub.view_entry')
    return render(request, 'hub/detail.html', {'title': entry.title, 'entry': entry, 'is_preview': is_preview})

def download(request, slug):
    entry = get_object_or_404(visible_entries(request), slug=slug)
    if not entry.document:
        raise Http404
    try:
        stream = entry.document.open('rb')
    except FileNotFoundError:
        raise Http404
    response = FileResponse(stream, as_attachment=True, filename=f'{entry.slug}.pdf', content_type='application/pdf')
    response['Cache-Control'] = 'private, no-store'
    return response

def search(request):
    q = request.GET.get('q', '').strip()[:200]
    entries = Entry.objects.published().filter(Q(title__icontains=q) | Q(body__icontains=q) | Q(summary__icontains=q)) if q else Entry.objects.none()
    return render(request, 'hub/search.html', {'title': 'Search the information center', 'q': q, 'page_obj': Paginator(entries, 15).get_page(request.GET.get('page'))})

@staff_member_required
def editor(request):
    if not request.user.has_perm('hub.view_entry'):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request, 'hub/editor.html', {'title': 'Editorial desk', 'drafts': Entry.objects.exclude(status='published').order_by('-updated_at')[:15], 'recent': Entry.objects.order_by('-updated_at')[:10], 'counts': [{'label': label, 'kind': kind, 'count': Entry.objects.filter(kind=kind).count()} for kind, label in Entry.KINDS]})

def health(request):
    Entry.objects.exists()
    return JsonResponse({'status': 'ok'})

def robots(request):
    return HttpResponse('User-agent: *\nDisallow: /admin/\nDisallow: /editor/\nDisallow: /*?preview=\n', content_type='text/plain')
