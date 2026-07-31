#!/usr/bin/env python3
"""Find the true source photo for each published portrait, by face content.

Filename matching proved unreliable: it paired a portrait with an illustration
of that person, with an entirely different person who happened to share a
filename, and with a genuine but much older photo. None of those are the
original the published crop was cut from.

This compares faces instead. Every image is run through YuNet face detection;
the largest face is cropped, greyscaled, normalised and reduced to a fixed
size. A published portrait and its true source contain the *same photographed
face*, so their normalised crops correlate very highly, while a different
photo of the same person does not.

Two numbers are reported per candidate:

  score      normalised cross-correlation of the face crops, -1..1.
             Above ~0.9 means almost certainly the same photograph.
  face_px    the size of the face in the candidate, which is what actually
             limits portrait quality. A face 700px wide in a tight photo beats
             one padded out inside a 4032px frame.

Usage:
    verify_portrait_sources.py --portraits static/img/member static/img/collaborator \
                               --candidates images --model scripts/models/face_detection_yunet_2023mar.onnx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CROP = 96          # face crops are compared at this resolution
MARGIN = 0.35      # extra context around the detected box, as a fraction
DETECT_MAX = 1600  # downscale before detection; YuNet is slower on huge frames


def load_detector(model: Path, cv2):
    if not model.exists():
        raise SystemExit(f"face model not found: {model}")
    return cv2.FaceDetectorYN.create(str(model), "", (320, 320), 0.6, 0.3, 5000)


def face_crop(path: Path, detector, cv2, np):
    """Return (normalised face crop, face pixel size) or (None, 0)."""
    raw = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        return None, 0
    h, w = img.shape[:2]
    if max(h, w) == 0:
        return None, 0

    scale = min(1.0, DETECT_MAX / max(h, w))
    small = cv2.resize(img, (int(w * scale), int(h * scale))) if scale < 1.0 else img
    sh, sw = small.shape[:2]
    detector.setInputSize((sw, sh))
    try:
        _, faces = detector.detect(small)
    except cv2.error:
        return None, 0
    if faces is None or len(faces) == 0:
        return None, 0

    # largest detection wins; portraits and group shots both behave sensibly
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])[:4]
    mx, my = fw * MARGIN, fh * MARGIN
    x0, y0 = max(0, int(x - mx)), max(0, int(y - my))
    x1, y1 = min(sw, int(x + fw + mx)), min(sh, int(y + fh + my))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None, 0

    crop = cv2.cvtColor(small[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    crop = cv2.resize(crop, (CROP, CROP)).astype(np.float32)
    crop -= crop.mean()
    norm = np.linalg.norm(crop)
    if norm < 1e-6:
        return None, 0
    # face size expressed in the ORIGINAL image's pixels
    return crop / norm, int(fw / scale)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portraits", type=Path, nargs="+", required=True)
    parser.add_argument("--candidates", type=Path, nargs="+", required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--top", type=int, default=3)
    args = parser.parse_args()

    try:
        import cv2
        import numpy as np
    except ImportError:
        print("opencv-python-headless and numpy are required", file=sys.stderr)
        return 1

    detector = load_detector(args.model, cv2)
    exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}

    published = []
    for root in args.portraits:
        for f in sorted(root.rglob("*")):
            if f.is_file() and f.suffix.lower() in exts:
                published.append(f)

    seen: set[Path] = set()
    candidates = []
    for root in args.candidates:
        for f in sorted(root.rglob("*")):
            if f.is_file() and f.suffix.lower() in exts and f not in seen:
                seen.add(f)
                candidates.append(f)

    print(f"published portraits: {len(published)}   candidate images: {len(candidates)}")
    print("detecting faces …")

    pub_faces = {}
    for f in published:
        crop, px = face_crop(f, detector, cv2, np)
        if crop is not None:
            pub_faces[f] = crop
    print(f"  faces found in {len(pub_faces)}/{len(published)} published portraits")

    cand_faces = []
    for i, f in enumerate(candidates, 1):
        if i % 100 == 0:
            print(f"  … {i}/{len(candidates)}")
        crop, px = face_crop(f, detector, cv2, np)
        if crop is not None:
            cand_faces.append((f, crop, px))
    print(f"  faces found in {len(cand_faces)}/{len(candidates)} candidates")

    results = []
    for f in published:
        crop = pub_faces.get(f)
        if crop is None:
            results.append({"portrait": str(f), "error": "no face detected", "matches": []})
            continue
        scored = []
        for cf, ccrop, px in cand_faces:
            if cf.resolve() == f.resolve():
                continue
            scored.append((float((crop * ccrop).sum()), px, str(cf)))
        scored.sort(reverse=True)
        results.append({
            "portrait": str(f),
            "matches": [{"score": round(s, 4), "face_px": px, "path": p}
                        for s, px, p in scored[:args.top]],
        })

    if args.json:
        args.json.write_text(json.dumps(results, indent=1))
        print(f"\nwrote {args.json}")

    strong = [r for r in results if r.get("matches") and r["matches"][0]["score"] >= 0.90]
    likely = [r for r in results if r.get("matches") and 0.75 <= r["matches"][0]["score"] < 0.90]
    weak = [r for r in results if r.get("matches") and r["matches"][0]["score"] < 0.75]
    print(f"\nsame photograph (>=0.90):  {len(strong)}")
    print(f"probable      (0.75-0.90): {len(likely)}")
    print(f"no real match (<0.75):     {len(weak)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
