#!/usr/bin/env python3
"""Convert Academic-era person pages into HugoBlox `data/authors/*.yaml`.

Reads the TOML front matter of `content/member/*.md` and
`content/collaborator/*.md` from the pre-migration site and writes one
`data/authors/<slug>.yaml` per person.

The slug is derived from the first `author_names` entry, urlized, because that
is the key HugoBlox uses to join a publication's `authors` taxonomy term to a
profile (see `layouts/authors/term.html`: `.Data.Term | urlize`). People who
appear in both content/member/ and content/collaborator/ collapse into a single
file carrying both user groups.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
import unicodedata
from pathlib import Path

# Icons in the old site come from Font Awesome pack+name pairs; HugoBlox uses
# its own icon namespace. Only the ones this site actually uses are mapped.
ICON_MAP = {
    ("fas", "envelope"): "at-symbol",
    ("fas", "phone"): "hero/phone",
    ("fab", "twitter"): "brands/x",
    ("fab", "github"): "brands/github",
    ("fab", "linkedin"): "brands/linkedin",
    ("ai", "google-scholar"): "academicons/google-scholar",
    ("ai", "orcid"): "academicons/orcid",
    ("ai", "researchgate"): "academicons/researchgate",
    ("ai", "cv"): "hero/document-text",
}

# Suffixes that are part of the display name but must not be read as a surname.
POSTNOMINAL_RE = re.compile(
    r",?\s*\b(Ph\.?D\.?|M\.?D\.?|M\.?S\.?|D\.?Phil\.?|Dr\.?)\s*$", re.IGNORECASE
)


def urlize(value: str) -> str:
    """Approximate Hugo's `urlize` under `removePathAccents: true`.

    Accents must be folded: Hugo emits the author taxonomy term for
    "R Campos-Sánchez" at /authors/r-campos-sanchez/, and
    `get_author_profile` looks the profile up by that folded slug. A data file
    named with the accent kept would silently never be found.
    """
    value = unicodedata.normalize("NFKD", value.strip().lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return _slugify(value)


def term_slug(value: str) -> str:
    """Hugo's taxonomy *term key*, which keeps diacritics.

    A publication citing "E Torres-González" produces the term `e-torres-gonzález`
    and, because `removePathAccents` is on, publishes it at
    /authors/e-torres-gonzalez/. An author stub directory named with the folded
    form would be a *second* term competing for that same path, which Hugo
    rejects as a duplicate target. Stub directories must therefore use this
    accent-preserving form while the data file uses the folded `urlize` form.
    """
    return _slugify(value.strip().lower())


def _slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    return re.sub(r"-{2,}", "-", value).strip("-")


def split_front_matter(text: str) -> tuple[dict, str]:
    """Return (front matter, body) for a `+++`-delimited TOML page."""
    if not text.startswith("+++"):
        raise ValueError("expected TOML front matter delimited by +++")
    _, fm, body = text.split("+++", 2)
    return tomllib.loads(fm), body.strip()


def display_and_family(name: str) -> tuple[str, str]:
    """Split a display name into (display, family), ignoring postnominals."""
    display = name.strip()
    bare = POSTNOMINAL_RE.sub("", display).strip().rstrip(",")
    family = bare.split()[-1] if bare else ""
    return display, family


def convert_links(fm: dict) -> list[dict]:
    links: list[dict] = []
    for social in fm.get("social", []):
        url = (social.get("link") or "").strip()
        if not url:
            continue
        key = (social.get("icon_pack", "fas"), social.get("icon", ""))
        links.append({"icon": ICON_MAP.get(key, "link"), "url": url})
    for field, icon, label in (
        ("personal_website", "hero/globe-alt", "Website"),
        ("cv_link", "hero/document-text", "Curriculum vitae"),
    ):
        url = (fm.get(field) or "").strip()
        if url:
            links.append({"icon": icon, "url": url, "label": label})
    return links


def convert_education(fm: dict) -> list[dict]:
    education = []
    for entry in fm.get("education", []):
        item = {
            "degree": entry.get("course", ""),
            "institution": entry.get("institution", ""),
        }
        if entry.get("year"):
            item["end"] = f"{entry['year']}-01-01"
        education.append(item)
    return education


def convert_person(path: Path, kind: str) -> tuple[str, dict, str]:
    """Convert one person page. Returns (slug, profile, legacy_url)."""
    fm, body = split_front_matter(path.read_text(encoding="utf-8"))

    author_names = fm.get("author_names") or []
    # Fall back to the display name when a person is never cited; the profile
    # still renders, it just will not join to any publication.
    slug = urlize(author_names[0]) if author_names else urlize(fm.get("name", path.stem))

    display, family = display_and_family(fm.get("name", ""))
    former = fm.get("is_former_member") or fm.get("is_former_collaborator") or False

    if kind == "member":
        group = "Former Members" if former else "Members"
    else:
        group = "Former Collaborators" if former else "Collaborators"

    profile: dict = {
        "schema": "hugoblox/author/v1",
        "slug": slug,
        "name": {"display": display, "family": family},
        "user_groups": [group],
        # `sort_position` was the old manual ordering key; team-showcase sorts
        # `weight` numerically (block.html special-cases it).
        #
        # Shifted by one so no weight is ever 0. team-showcase resolves the sort
        # key with `$primary | default $missingSentinel` (block.html:186,403),
        # and Go templates treat 0 as empty — so `weight: 0` is read as "no
        # weight" and sorts *last* under the 999999 sentinel. Kateryna had
        # sort_position 0 and landed at the end of the members list.
        "weight": fm.get("sort_position", 0) + 1,
    }

    if fm.get("role"):
        profile["role"] = fm["role"]
    # The page body is the long biography; short_bio was the card blurb. Only
    # one `bio` field exists, so prefer the body and let the card clamp it.
    bio = body or fm.get("short_bio", "")
    if bio:
        profile["bio"] = bio
    if fm.get("interests"):
        profile["interests"] = fm["interests"]

    affiliations = [
        {"name": org.get("name", ""), "role": org.get("role", "")}
        for org in fm.get("organizations", [])
        if org.get("name")
    ]
    if affiliations:
        profile["affiliations"] = affiliations
    if education := convert_education(fm):
        profile["education"] = education
    if links := convert_links(fm):
        profile["links"] = links

    # Every alternate spelling must resolve to this profile, otherwise a
    # publication citing the other spelling creates an orphan taxonomy term.
    alternates = [urlize(n) for n in author_names[1:]]
    if alternates:
        profile["_alternate_slugs"] = alternates

    term = term_slug(author_names[0]) if author_names else slug
    return slug, profile, f"/{kind}/{path.stem}/", term


def merge(existing: dict, new: dict) -> dict:
    """Merge a collaborator record into an existing member record (or vice versa)."""
    merged = dict(existing)
    merged["user_groups"] = sorted(set(existing["user_groups"]) | set(new["user_groups"]))
    for key, value in new.items():
        if key not in merged or not merged[key]:
            merged[key] = value
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="pre-migration site root (holds content/member/)")
    parser.add_argument("--dest", type=Path, required=True,
                        help="target site root (data/authors/ is written here)")
    args = parser.parse_args()

    try:
        import yaml
    except ImportError:
        print("PyYAML is required: pip install pyyaml", file=sys.stderr)
        return 1

    profiles: dict[str, dict] = {}
    aliases: dict[str, list[str]] = {}
    terms: dict[str, str] = {}
    failures: list[str] = []

    for kind in ("member", "collaborator"):
        for path in sorted((args.source / "content" / kind).glob("*.md")):
            if path.name == "_index.md":
                continue
            try:
                slug, profile, legacy, term = convert_person(path, kind)
            except Exception as exc:  # noqa: BLE001 - report and keep going
                failures.append(f"{path}: {exc}")
                continue
            profiles[slug] = merge(profiles[slug], profile) if slug in profiles else profile
            aliases.setdefault(slug, []).append(legacy)
            terms.setdefault(slug, term)

    out_dir = args.dest / "data" / "authors"
    out_dir.mkdir(parents=True, exist_ok=True)
    for slug, profile in profiles.items():
        (out_dir / f"{slug}.yaml").write_text(
            yaml.safe_dump(profile, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )

    # Emitted separately so the alias-stub generator can consume them.
    (args.dest / "data" / "legacy_person_urls.yaml").write_text(
        yaml.safe_dump(aliases, sort_keys=True, allow_unicode=True), encoding="utf-8"
    )
    (args.dest / "data" / "author_term_slugs.yaml").write_text(
        yaml.safe_dump(terms, sort_keys=True, allow_unicode=True), encoding="utf-8"
    )

    print(f"wrote {len(profiles)} profiles to {out_dir}")
    for failure in failures:
        print(f"FAILED {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
