from django import template
from django.utils.html import format_html, format_html_join

register = template.Library()

@register.filter
def prose(value):
    parts = []
    for paragraph in value.replace('\r\n', '\n').split('\n\n'):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if paragraph.startswith('## '):
            parts.append(format_html('<h2>{}</h2>', paragraph[3:]))
        else:
            parts.append(format_html('<p>{}</p>', paragraph))
    return format_html_join('\n', '{}', ((part,) for part in parts))
