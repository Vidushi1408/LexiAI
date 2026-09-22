# webapp/markdown_utils.py
"""
Render LLM output (briefings, Q&A answers) as markdown safely.

The text comes from the model, which in turn saw untrusted document content, so it is rendered to
HTML and then sanitised down to a small allow-list before being marked safe for the template —
never trust it just because it came out of the same prompt that told it not to misbehave.
"""
import markdown as _markdown
import nh3
from markupsafe import Markup

_ALLOWED_TAGS = {"p", "br", "strong", "em", "b", "i", "ul", "ol", "li", "h1", "h2", "h3", "h4",
                 "blockquote", "code", "pre", "hr", "a", "table", "thead", "tbody", "tr", "th", "td"}
_ALLOWED_ATTRS = {"a": {"href", "title"}}


def render_markdown(text: str | None) -> Markup:
    if not text:
        return Markup("")
    html = _markdown.markdown(text, extensions=["extra", "sane_lists"])
    clean = nh3.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, link_rel="noopener noreferrer nofollow")
    return Markup(clean)
