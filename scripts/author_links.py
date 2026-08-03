#!/usr/bin/env python3
"""Work out which author names in publications are lab people, and write the map.

Publications list authors as free text -- "KD Makova", "EE Eichler", "W-H Li" --
and the theme makes every one of them a link, because `author` is a taxonomy and
Hugo mints a term page for each distinct string. That gives 1,243 author pages,
almost all of them for people with no connection to the lab.

This writes data/author_links.yaml, mapping the author strings that really are
lab members or collaborators to their slug. The template links a name only when
it appears there, so everyone else is rendered as plain text.

Four sources, most trustworthy first:

  0. data/author_names_extra.yaml, hand written and never overwritten. This is
     where to record anything the rules cannot reach -- above all a change of
     name. Melissa Wilson Sayres publishes as both MA Wilson and MA Wilson
     Sayres, and the only reason this site links both is that someone wrote them
     down years ago; no rule about surnames could have connected them, and the
     same will be true the next time somebody marries or changes their name.
  1. `author_names` from the old site's member and collaborator pages. Hand
     written, and the reason the old site could match "A Sarwar" to Adil Sarwar.
  2. The person's display name and their slug.
  3. Initial-plus-surname forms found in the publications themselves, accepted
     only when the initials do not contradict the ones already known.

Rule 3 cannot go on surname alone. The lab has an Xinru Zhang, a Di Chen, a
Carolyn Rogers and a Hui Zhao; the publications also contain Y Zhang, Y Chen,
J Rogers and S Zhao, who are other people entirely. Nor is the first initial
enough: Robert S Harris is in the lab and RA Harris is not, and Christian Huber
publishes as Ch Huber while CD Huber is someone else.

So the initials of the two names have to be prefix-compatible with the fullest
form already on record -- "EE Eichler" against "E Eichler", "SJ Craig" against
"SJC Craig", "K Makova" against "KD Makova" all pass, while "ra" against "rs"
and "cd" against "ch" do not. Everything rejected is printed, since a genuine
variant could be sitting among them.

Run from the repository root:

    python3 scripts/author_links.py            # write the map, report rejects
    python3 scripts/author_links.py --dry-run  # report only
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import unicodedata
from collections import defaultdict

OLD_SITE = "/home/rcb112/project/claude/lab-website"
HONORIFICS = re.compile(r"\b(phd|ph d|md|dr|prof|jr|sr|iii|ii)\b")


def norm(s: str) -> str:
    """Fold a name to something comparable: no accents, case, punctuation or titles."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace(".", " ").replace(",", " ").replace("-", " ")
    s = HONORIFICS.sub(" ", s)
    return " ".join(s.split())


def fold(s: str) -> str:
    """Drop accents. The author content directories keep them (e-torres-gonzález)
    while the data files are folded (e-torres-gonzalez.yaml), so a slug taken
    from one will not open the other."""
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def url_slugs() -> dict[str, str]:
    """folded slug -> the slug as it appears in the URL, accents and all."""
    out = {}
    for f in glob.glob("content/authors/*/_index.md"):
        slug = os.path.basename(os.path.dirname(f))
        out[fold(slug)] = slug
    return out


def old_id_to_slug() -> dict[str, str]:
    """The migration left /member/<id>/ and /collaborator/<id>/ aliases on each
    author page, which is the only thing tying the two sites' names together."""
    out = {}
    for f in glob.glob("content/authors/*/_index.md"):
        slug = fold(os.path.basename(os.path.dirname(f)))
        for a in re.findall(r"^- (/(?:member|collaborator)/\S+)", open(f).read(), re.M):
            out[a.strip("/").split("/")[-1]] = slug
    return out


def lab_people() -> dict[str, dict]:
    """slug -> display name, family name, and first initial, from the data files."""
    people = {}
    for p in glob.glob("data/authors/*.yaml"):
        slug = os.path.basename(p)[:-5]
        s = open(p).read()
        display = re.search(r"^\s*display:\s*(.+)$", s, re.M)
        family = re.search(r"^\s*family:\s*(.+)$", s, re.M)
        display = display.group(1).strip() if display else slug
        family = family.group(1).strip() if family else display.split()[-1]
        people[slug] = {
            "display": display,
            "family": norm(family),
            "initials": set(),   # filled in from every name we know for them
        }
    return people


def curated_names(id_map: dict[str, str]) -> dict[str, set[str]]:
    """`name` and `author_names` off the old site's people pages."""
    out = defaultdict(set)
    files = sorted(glob.glob(OLD_SITE + "/content/member/*.md"))
    files += sorted(glob.glob(OLD_SITE + "/content/collaborator/*.md"))
    for f in files:
        oid = os.path.basename(f)[:-3]
        slug = id_map.get(oid)
        if not slug:
            continue
        s = open(f).read()
        m = re.search(r'^name = "(.*?)"', s, re.M)
        if m:
            out[slug].add(m.group(1))
        m = re.search(r"^author_names = \[(.*?)\]", s, re.M | re.S)
        if m:
            out[slug].update(x for x in re.findall(r'"([^"]+)"', m.group(1)) if x.strip())
    return out


def extra_names() -> dict[str, list[str]]:
    """slug -> extra spellings, from the hand-written supplement."""
    path = "data/author_names_extra.yaml"
    if not os.path.exists(path):
        return {}
    out, slug = {}, None
    for line in open(path):
        line = line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith((" ", "\t", "-")) and line.endswith(":"):
            slug = line[:-1].strip()
            out[slug] = []
        elif slug and line.strip().startswith("-"):
            out[slug].append(line.strip()[1:].strip().strip("\"'"))
    return out


def initials_of(name: str, family: str) -> str:
    """The given-name part reduced to initials.

    A short token is already an initials block ("EE Eichler" -> ee), a long one
    is a name to take the first letter of ("Evan E. Eichler" -> ee).
    """
    key = norm(name)
    if key.endswith(family):
        key = key[: -len(family)]
    out = ""
    for tok in key.split():
        out += tok if len(tok) <= 3 else tok[0]
    return out


def publication_authors() -> dict[str, int]:
    """Every author string in the publications, with how often it appears."""
    counts: dict[str, int] = defaultdict(int)
    for f in glob.glob("content/publication/*.md"):
        m = re.search(r"^authors:\s*\n((?:\s*-\s*.*\n)+)", open(f).read(), re.M)
        if not m:
            continue
        for a in re.findall(r"-\s*(.+)", m.group(1)):
            a = a.strip().strip("\"'")
            if a:
                counts[a] += 1
    return counts


def path_hint(slug: str) -> str:
    return f"data/author_names_extra.yaml: {slug}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir("data/authors"):
        print("run me from the repository root", file=sys.stderr)
        return 1

    people = lab_people()
    curated = curated_names(old_id_to_slug())
    pubs = publication_authors()
    extra = extra_names()

    # normalised name -> slug, from the trustworthy sources
    known: dict[str, str] = {}
    for slug, names in extra.items():
        if slug not in people:
            print(f"warning: {path_hint(slug)} names a slug that does not exist", file=sys.stderr)
            continue
        for n in names:
            known[norm(n)] = slug
    for slug, names in curated.items():
        for n in names:
            known.setdefault(norm(n), slug)
    for slug, info in people.items():
        known.setdefault(norm(info["display"]), slug)
        known.setdefault(norm(slug.replace("-", " ")), slug)

    # every spelling we already trust contributes to what that person's
    # initials may look like; the longest is the one to test against
    for key, slug in known.items():
        people[slug]["initials"].add(initials_of(key, people[slug]["family"]))
    for slug, info in people.items():
        info["initials"].discard("")
        info["longest"] = max(info["initials"], key=len) if info["initials"] else ""

    by_family = defaultdict(list)
    for slug, info in people.items():
        by_family[info["family"]].append(slug)

    links: dict[str, str] = {}
    claimed, rejected = [], []
    for raw, n in sorted(pubs.items(), key=lambda kv: -kv[1]):
        key = norm(raw)
        if key in known:
            links[raw] = known[key]
            continue
        parts = key.split()
        if len(parts) < 2:
            continue
        family = parts[-1]
        for slug in by_family.get(family, []):
            mine = initials_of(key, family)
            theirs = people[slug]["longest"]
            if mine and theirs and (mine.startswith(theirs) or theirs.startswith(mine)):
                links[raw] = slug
                claimed.append((n, raw, slug, theirs))
            else:
                rejected.append((n, raw, slug, people[slug]["display"], theirs))

    if extra:
        print(f"hand-written extra spellings   : {sum(len(v) for v in extra.values())}"
              f" for {len(extra)} people")
    print(f"author strings in publications : {len(pubs)}")
    print(f"resolved to a lab person       : {len(links)}")
    print(f"  of those, matched on initial : {len(claimed)}")
    print(f"lab people with at least one   : {len(set(links.values()))} of {len(people)}")

    if claimed:
        print("\nmatched by initial + surname (check these read correctly):")
        for n, raw, slug, theirs in sorted(claimed, reverse=True):
            print(f"  {n:3}  {raw:32} -> {slug:18} (known as {theirs})")
    if rejected:
        print("\nsame surname, different initial -- left unlinked:")
        for n, raw, slug, disp, theirs in sorted(rejected, reverse=True):
            print(f"  {n:3}  {raw:32} is not {disp} ({theirs or slug})")

    if args.dry_run:
        return 0

    urls = url_slugs()
    with open("data/author_links.yaml", "w") as fh:
        fh.write("# Generated by scripts/author_links.py -- do not hand edit.\n")
        fh.write("#\n")
        fh.write("# Author strings in publications that belong to a lab member or\n")
        fh.write("# collaborator, mapped to their slug. The citation template links a\n")
        fh.write("# name only if it is in here, so that the 1,200-odd co-authors from\n")
        fh.write("# elsewhere are not given author pages on this site.\n")
        fh.write("#\n")
        fh.write("# Re-run the script after adding publications or people.\n")
        for raw in sorted(links):
            fh.write(f'"{raw}": {urls.get(links[raw], links[raw])}\n')
    print(f"\nwrote data/author_links.yaml with {len(links)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
