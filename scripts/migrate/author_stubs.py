#!/usr/bin/env python3
"""Generate `content/authors/<slug>/_index.md` stubs for every lab profile.

Two problems are solved here.

1. `/authors/<slug>/` pages are *taxonomy term pages*. A term only exists if
   some content page cites it, so a person who has never appeared in a
   publication's `authors` list gets no page — while `team-showcase` links to
   one regardless. On this site that is 20 of 84 profiles. An explicit stub
   creates the term, and `layouts/authors/term.html` still fills it from
   `data/authors/<slug>.yaml`.

2. The old site published people at `/member/<file>/` and
   `/collaborator/<file>/`. Those URLs are carried over as `aliases` so nothing
   that links to them breaks.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path


def fold(value: str) -> str:
    """Accent-folded slug — matches `urlize` under `removePathAccents: true`."""
    value = unicodedata.normalize("NFKD", value.strip().lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    return re.sub(r"-{2,}", "-", value).strip("-")


def term_of(value: str) -> str:
    """Hugo's taxonomy term key, which preserves diacritics."""
    value = re.sub(r"[^\w\s-]", "", value.strip().lower())
    value = re.sub(r"[\s_]+", "-", value)
    return re.sub(r"-{2,}", "-", value).strip("-")


def terms_from_publications(site: Path, yaml) -> dict[str, str]:
    """Map folded slug -> the term key the publications actually generate.

    Authoritative over anything derived from the old person pages: if a
    publication cites "H Pálová", Hugo creates the term `h-pálová`, and a stub
    directory named `h-palova` would be a second term on the same URL.
    """
    found: dict[str, str] = {}
    for path in sorted((site / "content" / "publication").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        head, sep, _ = text[4:].partition("\n---\n")
        if not sep:
            continue
        for author in (yaml.safe_load(head) or {}).get("authors") or []:
            found.setdefault(fold(author), term_of(author))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("."),
                        help="site root holding data/authors/ (default: cwd)")
    args = parser.parse_args()

    try:
        import yaml
    except ImportError:
        print("PyYAML is required: pip install pyyaml", file=sys.stderr)
        return 1

    authors_dir = args.site / "data" / "authors"
    if not authors_dir.is_dir():
        print(f"no such directory: {authors_dir}", file=sys.stderr)
        return 1

    legacy_path = args.site / "data" / "legacy_person_urls.yaml"
    legacy = yaml.safe_load(legacy_path.read_text()) if legacy_path.exists() else {}

    # The stub *directory* must be Hugo's taxonomy term key, which keeps
    # diacritics, or an accented name yields two terms fighting over one URL.
    terms_path = args.site / "data" / "author_term_slugs.yaml"
    terms = yaml.safe_load(terms_path.read_text()) if terms_path.exists() else {}
    # Publications win: they are what actually creates the taxonomy terms.
    terms.update(terms_from_publications(args.site, yaml))

    written = 0
    for profile_path in sorted(authors_dir.glob("*.yaml")):
        slug = profile_path.stem
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
        title = (profile.get("name") or {}).get("display") or slug

        front: dict = {"title": title}
        if aliases := legacy.get(slug):
            front["aliases"] = aliases

        out_dir = args.site / "content" / "authors" / terms.get(slug, slug)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "_index.md").write_text(
            "---\n"
            + yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
            + "---\n",
            encoding="utf-8",
        )
        written += 1

    print(f"wrote {written} author stubs under {args.site / 'content' / 'authors'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
