import html
import re

COPY_BLOCK_RE = re.compile(
    r"```copy\s+(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def preprocess_copy_blocks(text: str) -> str:
    """
    Replace ```copy blocks with HTML that supports click-to-copy.

    This runs BEFORE markdown rendering.
    """
    if not text:
        return text

    def replacer(match):
        raw_content = match.group(1).strip()
        escaped = html.escape(raw_content)

        return f"""
<div class="copy-block">
  <button type="button" class="copy-btn" title="Copy to clipboard">
    Copy
  </button>
  <pre class="copy-content">{escaped}</pre>
</div>
"""

    return COPY_BLOCK_RE.sub(replacer, text)
