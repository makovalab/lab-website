#!/usr/bin/env python3
"""Repoint `{{< ref "/member/..." >}}` shortcodes at the new author pages.

`content/member/` and `content/collaborator/` stop being content once people
move to `data/authors/`, so every `ref` aimed at them becomes a build-breaking
REF_NOT_FOUND. The author stubs written by `author_stubs.py` are valid ref
targets, so each reference is rewritten to `/authors/<slug>`.

The mapping comes from `data/legacy_person_urls.yaml`, which
`people_to_authors.py` emits as slug -> [legacy URL, ...].
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REF_RE = re.compile(
    r'(\{\{<\s*ref\s+")(/(?:member|collaborator|authors)/[^"]+?)("\s*>\}\})'
)


def build_index(legacy: dict[str, list[str]], terms: dict[str, str]) -> dict[str, str]:
    """Map every legacy person path form onto its author *term* slug.

    The ref target must be the taxonomy term key (which keeps diacritics), not
    the accent-folded data-file slug — that is the directory `author_stubs.py`
    creates. Already-rewritten `/authors/<folded>` refs are accepted as input so
    the script is safe to re-run.
    """
    index: dict[str, str] = {}
    for slug, urls in legacy.items():
        term = terms.get(slug, slug)
        # Both the folded and the term form map onto the term, so re-running the
        # script over already-rewritten content is a no-op rather than an error.
        for existing in {slug, term}:
            for form in (f"/authors/{existing}", f"/authors/{existing}/"):
                index[form] = term
        for url in urls:
            stem = url.strip("/").split("/")[-1]          # e.g. kateryna_makova
            section = url.strip("/").split("/")[0]        # member | collaborator
            for form in (
                f"/{section}/{stem}.md",
                f"/{section}/{stem}",
                f"/{section}/{stem}/",
            ):
                index[form] = term
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("."))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        import yaml
    except ImportError:
        print("PyYAML is required: pip install pyyaml", file=sys.stderr)
        return 1

    legacy_path = args.site / "data" / "legacy_person_urls.yaml"
    if not legacy_path.exists():
        print(f"missing {legacy_path}; run people_to_authors.py first", file=sys.stderr)
        return 1
    terms_path = args.site / "data" / "author_term_slugs.yaml"
    terms = yaml.safe_load(terms_path.read_text()) if terms_path.exists() else {}
    index = build_index(yaml.safe_load(legacy_path.read_text()), terms)

    rewritten = 0
    unresolved: list[str] = []
    touched: set[Path] = set()

    for path in sorted((args.site / "content").rglob("*.md")):
        text = path.read_text(encoding="utf-8")

        def replace(match: re.Match[str]) -> str:
            nonlocal rewritten
            target = match.group(2)
            slug = index.get(target)
            if slug is None:
                unresolved.append(f"{path}: {target}")
                return match.group(0)
            rewritten += 1
            return f"{match.group(1)}/authors/{slug}{match.group(3)}"

        new_text = REF_RE.sub(replace, text)
        if new_text != text:
            touched.add(path)
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8")

    verb = "would rewrite" if args.dry_run else "rewrote"
    print(f"{verb} {rewritten} person refs across {len(touched)} files")
    for item in unresolved:
        print(f"UNRESOLVED {item}", file=sys.stderr)
    return 1 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
