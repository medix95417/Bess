import hashlib
from django.core.cache import cache
from django.http import HttpResponse

class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        # Leaflet uses inline style attributes for map positioning; scripts remain same-origin.
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://tile.openstreetmap.org; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
        if request.path.startswith(('/editor/', '/admin/')) or request.GET.get('preview'):
            response['Cache-Control'] = 'private, no-store'
            response['X-Robots-Tag'] = 'noindex, nofollow'
        return response

class LoginThrottleMiddleware:
    """Per-account failed-login limit. Shared file cache survives worker restarts."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path != '/admin/login/' or request.method != 'POST':
            return self.get_response(request)
        username = request.POST.get('username', '').casefold()
        key = 'login:' + hashlib.sha256(username.encode()).hexdigest()
        failures = cache.get(key, 0)
        if failures >= 10:
            result = HttpResponse('Too many unsuccessful sign-in attempts. Try again in 15 minutes.', status=429, content_type='text/plain')
            result['Retry-After'] = '900'
            return result
        response = self.get_response(request)
        if response.status_code == 302 and request.user.is_authenticated:
            cache.delete(key)
        elif response.status_code == 200:
            cache.set(key, failures + 1, 900)
        return response
