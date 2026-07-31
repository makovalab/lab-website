#!/usr/bin/env python3
"""Collapse author-name spelling variants in publication front matter.

HugoBlox turns each `authors:` entry into a taxonomy term, and the term's URL
is the accent-folded slug. Two spellings of one person that differ only by a
diacritic or an apostrophe style therefore produce two distinct terms competing
for the same output path, which Hugo reports as a duplicate target path.

On this site five people are affected, e.g. "RJ O'Neill" vs "RJ O’Neill" and
"E Kejnovsky" vs "E Kejnovský". The canonical spelling chosen here is the
richest one (accents kept, typographic apostrophe), since that is the person's
actual name and it still folds to the same ASCII URL.
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
import unicodedata
from pathlib import Path


def fold(value: str) -> str:
    """Accent- and punctuation-folded key used to group spellings of one name."""
    value = unicodedata.normalize("NFKD", value.strip().lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("’", "'")
    value = re.sub(r"[^\w\s'-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    return re.sub(r"-{2,}", "-", value).strip("-")


def richness(name: str) -> tuple[int, int, int]:
    """Rank spellings; the highest-ranked becomes canonical."""
    accents = sum(1 for ch in unicodedata.normalize("NFKD", name) if unicodedata.combining(ch))
    curly = name.count("’")
    return (accents, curly, len(name))


def split_front_matter(text: str) -> tuple[str, str] | None:
    """Return (front matter, rest) for a `---`-delimited YAML page."""
    if not text.startswith("---\n"):
        return None
    head, sep, rest = text[4:].partition("\n---\n")
    return (head, rest) if sep else None


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

    pubs = sorted((args.site / "content" / "publication").glob("*.md"))

    # Pass 1: collect every spelling of every folded name.
    spellings: dict[str, set[str]] = collections.defaultdict(set)
    for path in pubs:
        parts = split_front_matter(path.read_text(encoding="utf-8"))
        if not parts:
            continue
        fm = yaml.safe_load(parts[0]) or {}
        for author in fm.get("authors") or []:
            spellings[fold(author)].add(author)

    canonical = {
        key: max(variants, key=richness)
        for key, variants in spellings.items()
        if len(variants) > 1
    }
    if not canonical:
        print("no spelling variants found")
        return 0

    print(f"collapsing {len(canonical)} names with multiple spellings:")
    for key, chosen in sorted(canonical.items()):
        others = sorted(spellings[key] - {chosen})
        print(f"  {chosen!r}  <-  {others}")

    # Pass 2: rewrite. Only the individual author strings change, so the edit is
    # done on the raw text to leave the rest of the file byte-identical.
    changed = 0
    for path in pubs:
        text = path.read_text(encoding="utf-8")
        parts = split_front_matter(text)
        if not parts:
            continue
        head, rest = parts
        new_head = head
        for line in head.splitlines():
            match = re.match(r"^(- )(.+)$", line)
            if not match:
                continue
            author = match.group(2).strip()
            chosen = canonical.get(fold(author))
            if chosen and chosen != author:
                new_head = new_head.replace(f"- {author}\n", f"- {chosen}\n")
        if new_head != head:
            changed += 1
            if not args.dry_run:
                path.write_text(f"---\n{new_head}\n---\n{rest}", encoding="utf-8")

    verb = "would rewrite" if args.dry_run else "rewrote"
    print(f"{verb} {changed} publication files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
