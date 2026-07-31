#!/usr/bin/env python3
"""Convert Academic-era publication pages to the current HugoBlox front matter.

The old TOML front matter still *renders* on HugoBlox, but every page emits
deprecation warnings, and CI builds with `--panicOnWarning`. Three shapes
changed:

  publication_types = ["2"]     ->  publication_types: [article-journal]
  publication = "_Nature_"      ->  publication: {name: Nature, short_name: ...}
  doi = "10.1038/..."           ->  hugoblox: {ids: {doi: ...}}
  url_pdf = "https://..."       ->  links: [{type: pdf, url: "https://..."}]

Output is YAML because that is what the HugoBlox schemas are documented in, and
because re-emitting normalizes away the large Academic comment blocks that
document the now-obsolete numeric `publication_types` legend.

The build warning suggests `hugoblox migrate publications`; that command does
not exist in the CLI (only `v0.11.0-authors` and `v0.11.0-events` ship), which
is why this script exists.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

# Index into the old `publication_types` list -> CSL type.
CSL_TYPES = {
    "0": "manuscript",       # Uncategorized
    "1": "paper-conference",
    "2": "article-journal",
    "3": "manuscript",
    "4": "report",
    "5": "book",
    "6": "chapter",          # Book section
}

URL_FIELDS = [
    ("url_pdf", "pdf"),
    ("url_preprint", "preprint"),
    ("url_code", "code"),
    ("url_dataset", "dataset"),
    ("url_project", "project"),
    ("url_slides", "slides"),
    ("url_video", "video"),
    ("url_poster", "poster"),
    ("url_source", "source"),
]

# `publication` / `publication_short` carried Markdown emphasis (e.g. "_Nature_")
# because the old templates piped them through `markdownify`. The structured
# field is rendered as plain text, so the emphasis markers must come off.
EMPHASIS_RE = re.compile(r"^[_*]+(.*?)[_*]+$")


def strip_emphasis(value: str) -> str:
    value = value.strip()
    match = EMPHASIS_RE.match(value)
    return match.group(1).strip() if match else value


def split_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("+++"):
        raise ValueError("expected TOML front matter delimited by +++")
    _, fm, body = text.split("+++", 2)
    return tomllib.loads(fm), body.lstrip("\n")


def convert(fm: dict) -> dict:
    out: dict = {"title": fm["title"], "date": fm["date"]}

    if fm.get("authors"):
        out["authors"] = fm["authors"]

    types = [CSL_TYPES.get(str(t), "manuscript") for t in fm.get("publication_types", [])]
    if types:
        out["publication_types"] = types

    if name := strip_emphasis(fm.get("publication", "")):
        publication: dict = {"name": name}
        if short := strip_emphasis(fm.get("publication_short", "")):
            publication["short_name"] = short
        out["publication"] = publication

    for src, dest in (("abstract", "abstract"), ("abstract_short", "summary")):
        if value := (fm.get(src) or "").strip():
            out[dest] = value

    # `selected` became `featured`.
    if fm.get("selected"):
        out["featured"] = True
    if fm.get("draft"):
        out["draft"] = True

    for key in ("projects", "tags", "categories", "slides"):
        if value := fm.get(key):
            # `projects = [""]` appears in the old data; drop empty entries.
            if isinstance(value, list):
                value = [v for v in value if v]
                if not value:
                    continue
            out[key] = value

    links = [
        {"type": link_type, "url": url.strip()}
        for field, link_type in URL_FIELDS
        if (url := (fm.get(field) or "").strip())
    ]
    # `url_custom` was already a list of {name, url} pairs in Academic; it maps
    # onto a named link rather than a typed one.
    for custom in fm.get("url_custom") or []:
        if url := (custom.get("url") or "").strip():
            links.append({"name": custom.get("name", "Link").strip(), "url": url})
    if links:
        out["links"] = links

    if doi := (fm.get("doi") or "").strip():
        out["hugoblox"] = {"ids": {"doi": doi}}

    # Passed through unchanged; `image.caption` / `image.focal_point` are still
    # read by the current templates.
    for key in ("image", "header"):
        if value := fm.get(key):
            out[key] = value

    return out


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

    converted = 0
    skipped: list[str] = []
    failures: list[str] = []

    for path in sorted((args.site / "content" / "publication").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("+++"):
            skipped.append(str(path))
            continue
        try:
            fm, body = split_front_matter(text)
            out = convert(fm)
        except Exception as exc:  # noqa: BLE001 - report and keep going
            failures.append(f"{path}: {exc}")
            continue

        rendered = yaml.safe_dump(
            out, sort_keys=False, allow_unicode=True, width=1000, default_flow_style=False
        )
        if not args.dry_run:
            path.write_text(f"---\n{rendered}---\n\n{body}", encoding="utf-8")
        converted += 1

    verb = "would convert" if args.dry_run else "converted"
    print(f"{verb} {converted} publications")
    for item in skipped:
        print(f"SKIPPED (not TOML) {item}")
    for item in failures:
        print(f"FAILED {item}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
