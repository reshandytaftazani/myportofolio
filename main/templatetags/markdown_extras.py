from django import template
from django.template.defaultfilters import stringfilter
import markdown as md
import nh3

register = template.Library()

@register.filter(name='markdown')
@stringfilter
def markdown_format(text):
    html = md.markdown(text, extensions=['markdown.extensions.fenced_code', 'markdown.extensions.nl2br'])
    return nh3.clean(
        html,
        tags={'p', 'br', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
              'strong', 'em', 'b', 'i', 'del', 'blockquote', 'ul', 'ol', 'li',
              'pre', 'code', 'a'},
        attributes={'a': {'href', 'title'}, 'code': {'class'}},
        url_schemes={'http', 'https', 'mailto'},
        clean_content_tags={'script', 'style'},
        link_rel='noopener noreferrer',
    )
