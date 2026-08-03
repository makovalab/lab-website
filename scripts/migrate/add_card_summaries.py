#!/usr/bin/env python3
"""Give list-card pages an explicit plain-text `summary`.

The `date-title-summary` and `card` views render the summary inside a
`<p class="relative z-10">` (blox/.../views/date-title-summary.html:24). Many
news, press-release, project and video pages open with a `{{< figure >}}`, so
Hugo's auto-summary starts with a `<figure>` — which is not valid inside a
`<p>`, so the browser hoists it out of the paragraph.

Once hoisted it is no longer inside the `z-10` wrapper, while the card's hover
background (`absolute ... z-0 bg-zinc-50 opacity-0 group-hover:opacity-100`) is
positioned. On hover that opaque layer paints over the image and it vanishes.

Setting an explicit summary keeps the card text-only and leaves the page body,
and its figure, untouched.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECTIONS = ("news", "press_release", "project", "video")

SHORTCODE_RE = re.compile(r"\{\{[<%].*?[>%]\}\}", re.S)
HTML_TAG_RE = re.compile(r"<[^>]+>")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
MD_EMPHASIS_RE = re.compile(r"[*_`]{1,3}")


def plain_text(body: str) -> str:
    text = SHORTCODE_RE.sub(" ", body)
    text = HTML_TAG_RE.sub(" ", text)
    text = MD_LINK_RE.sub(r"\1", text)
    text = MD_EMPHASIS_RE.sub("", text)
    # Drop blockquote and heading markers, keeping their prose.
    text = re.sub(r"(?m)^\s*[>#]+\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, limit: int = 300) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut).rstrip(" ,;:") + "…"


def split_front_matter(text: str) -> tuple[str, str, str] | None:
    """Return (delimiter, front matter, body)."""
    for delim in ("+++", "---"):
        if text.startswith(delim + "\n"):
            head, sep, body = text[len(delim) + 1:].partition("\n" + delim + "\n")
            if sep:
                return delim, head, body
    return None


BLOCK_START_RE = re.compile(r"(\{\{[<%]\s*(figure|video|youtube)|<(div|figure|iframe|br|p|table)\b)")


def has_block_html_summary(body: str, word_budget: int = 60) -> bool:
    """Would Hugo's auto-summary contain block-level content?

    The auto-summary is the first `summaryLength` words (30 site-wide), so it is
    not enough to look at the first line: a page can open with a sentence and
    put the figure directly beneath it, still well inside the summary. Scan
    until the word budget — double summaryLength, for margin — is spent.
    """
    words = 0
    for line in body.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if BLOCK_START_RE.match(stripped):
            return True
        words += len(stripped.split())
        if words >= word_budget:
            return False
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("."))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    updated, skipped = 0, 0
    for section in SECTIONS:
        root = args.site / "content" / section
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name == "_index.md":
                continue
            text = path.read_text(encoding="utf-8")
            parts = split_front_matter(text)
            if not parts:
                continue
            delim, front, body = parts

            if re.search(r"(?m)^summary\s*[=:]", front):
                skipped += 1
                continue
            if not has_block_html_summary(body):
                continue

            summary = truncate(plain_text(body))
            if not summary:
                continue

            escaped = summary.replace("\\", "\\\\").replace('"', '\\"')
            line = (f'summary = "{escaped}"' if delim == "+++" else f'summary: "{escaped}"')
            # Prepended so it reads before the long comment blocks the Academic
            # archetypes left behind.
            new = f"{delim}\n{line}\n{front}\n{delim}\n{body}"
            if not args.dry_run:
                path.write_text(new, encoding="utf-8")
            updated += 1
            print(f"  {path.relative_to(args.site)}: {summary[:70]}…")

    verb = "would update" if args.dry_run else "updated"
    print(f"{verb} {updated} pages ({skipped} already had a summary)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
