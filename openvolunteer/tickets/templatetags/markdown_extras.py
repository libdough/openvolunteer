import markdown as md
from django import template

from .markdown_preprocess import preprocess_copy_blocks

register = template.Library()

MARKDOWN_EXTENSIONS = [
    "fenced_code",
    "tables",
    "sane_lists",
]


@register.filter
def render_markdown(text):
    if not text:
        return ""

    text = preprocess_copy_blocks(text)

    return md.markdown(
        text,
        extensions=MARKDOWN_EXTENSIONS,
        output_format="html5",
    )
