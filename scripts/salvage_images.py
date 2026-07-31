#!/usr/bin/env python3
"""Find every image under a directory by content, not by filename.

Written after an extension-based sweep of an archive missed 43 extensionless
files and 6 PDFs before that archive was deleted. This identifies files by
magic bytes, pulls images embedded in PDFs, and reports what it found *before*
anything is copied — so the source can be checked before it is removed.

Usage:
    salvage_images.py --source old --dest images/salvaged --known images/from-old
    salvage_images.py --source old --dest images/salvaged --known images/from-old --apply

Without --apply it only reports. `--known` may be repeated; anything whose
content hash already exists there is counted as a duplicate and not copied.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import io
import shutil
import sys
from pathlib import Path

# (offset, signature) pairs. Detection is by content because the archive is
# known to contain images saved without any extension.
SIGNATURES: list[tuple[int, bytes, str]] = [
    (0, b"\xff\xd8\xff", "jpeg"),
    (0, b"\x89PNG\r\n\x1a\n", "png"),
    (0, b"GIF87a", "gif"),
    (0, b"GIF89a", "gif"),
    (0, b"BM", "bmp"),
    (0, b"II*\x00", "tiff"),
    (0, b"MM\x00*", "tiff"),
    (0, b"\x00\x00\x01\x00", "ico"),
    (0, b"8BPS", "psd"),
    (4, b"ftypheic", "heic"),
    (4, b"ftypheix", "heic"),
    (4, b"ftypavif", "avif"),
]


def sniff(head: bytes) -> str | None:
    for offset, sig, kind in SIGNATURES:
        if head[offset:offset + len(sig)] == sig:
            return kind
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[:5] == b"%PDF-":
        return "pdf"
    # SVG is text; tolerate a leading XML declaration or comments.
    probe = head[:512].lstrip()
    if probe.startswith(b"<?xml") or probe.startswith(b"<svg") or probe.startswith(b"<!DOCTYPE svg"):
        if b"<svg" in head[:2048]:
            return "svg"
    return None


def load_known(paths: list[Path]) -> set[str]:
    known: set[str] = set()
    for root in paths:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file():
                known.add(hashlib.md5(f.read_bytes()).hexdigest())
    return known


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--known", type=Path, action="append", default=[],
                        help="directory of already-saved images (repeatable)")
    parser.add_argument("--apply", action="store_true",
                        help="actually copy; without this it only reports")
    parser.add_argument("--min-pixels", type=int, default=64,
                        help="ignore images smaller than this on the short side")
    args = parser.parse_args()

    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
    except ImportError:
        print("Pillow is required", file=sys.stderr)
        return 1

    known = load_known(args.known)
    print(f"already saved elsewhere: {len(known)} distinct images")

    kinds = collections.Counter()
    new: list[tuple[Path, str, tuple[int, int], bytes | None]] = []
    dupes = tiny = 0
    seen: set[str] = set()

    files = [f for f in args.source.rglob("*") if f.is_file()]
    print(f"scanning {len(files)} files under {args.source} …")

    for f in files:
        try:
            with f.open("rb") as fh:
                head = fh.read(4096)
        except OSError:
            continue
        kind = sniff(head)
        if kind is None:
            continue

        if kind == "pdf":
            # Embedded images are the reason PDFs are opened at all.
            try:
                import fitz
                doc = fitz.open(f)
            except Exception:
                continue
            for page in doc:
                for xref, *_ in page.get_images(full=True):
                    try:
                        raw = doc.extract_image(xref)
                    except Exception:
                        continue
                    blob = raw["image"]
                    digest = hashlib.md5(blob).hexdigest()
                    if digest in known or digest in seen:
                        dupes += 1
                        continue
                    try:
                        w, h = Image.open(io.BytesIO(blob)).size
                    except Exception:
                        continue
                    if min(w, h) < args.min_pixels:
                        tiny += 1
                        continue
                    seen.add(digest)
                    kinds["pdf-embedded"] += 1
                    new.append((f, f"pdf:{xref}.{raw['ext']}", (w, h), blob))
            doc.close()
            continue

        blob = f.read_bytes()
        digest = hashlib.md5(blob).hexdigest()
        if digest in known or digest in seen:
            dupes += 1
            continue
        if kind == "svg":
            size = (0, 0)
        else:
            try:
                size = Image.open(io.BytesIO(blob)).size
            except Exception:
                continue
            if min(size) < args.min_pixels:
                tiny += 1
                continue
        seen.add(digest)
        kinds[kind] += 1
        # Flag the files an extension-based sweep would have skipped.
        if not f.suffix or f.suffix.lower().lstrip(".") not in {
            "jpg", "jpeg", "png", "gif", "webp", "tif", "tiff", "svg", "ico", "bmp"
        }:
            kinds[f"  ^ would have been MISSED by extension ({kind})"] += 1
        new.append((f, kind, size, None))

    print(f"\nnew images not already saved: {len(new)}   duplicates: {dupes}   too small: {tiny}")
    for k, c in kinds.most_common():
        print(f"  {k}: {c}")

    big = sorted((n for n in new if n[2][0]), key=lambda n: -min(n[2]))[:25]
    if big:
        print("\nlargest new finds:")
        for src, kind, (w, h), _ in big:
            print(f"  {w:5d}x{h:<5d} {kind:14s} {src}")

    if not args.apply:
        print("\n(report only — pass --apply to copy these into the destination)")
        return 0

    args.dest.mkdir(parents=True, exist_ok=True)
    for src, kind, _, blob in new:
        rel = src.relative_to(args.source)
        if blob is None:
            out = args.dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out)
        else:
            tag = kind.replace(":", "_")
            out = args.dest / rel.with_name(f"{rel.stem}__{tag}")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(blob)
    print(f"\ncopied {len(new)} new images into {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
