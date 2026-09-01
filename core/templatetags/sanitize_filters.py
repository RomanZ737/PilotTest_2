from bleach.css_sanitizer import CSSSanitizer
import bleach
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'sub', 'sup',
    'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'pre', 'code',
    'a', 'img',
    'span', 'div', 'table', 'tr', 'td', 'th', 'thead', 'tbody',
]

ALLOWED_ATTRIBUTES = {
    '*': ['style', 'class', 'id'],
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'width', 'height'],
}

ALLOWED_CSS_PROPERTIES = [
    'text-align', 'padding-left', 'padding-right', 'padding-top', 'padding-bottom',
    'margin-left', 'margin-right', 'margin-top', 'margin-bottom',
    'color', 'background-color', 'font-weight', 'font-style', 'text-decoration',
    'width', 'height', 'border', 'border-radius',
    'display', 'float', 'vertical-align',
]

css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_CSS_PROPERTIES)

@register.filter(name='safe_html')
def safe_html(value):
    cleaned = bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=css_sanitizer,
        strip=False,
    )
    return mark_safe(cleaned)