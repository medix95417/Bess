from .models import SiteSettings

def site_context(request):
    return {'site': SiteSettings.objects.first() or SiteSettings()}
