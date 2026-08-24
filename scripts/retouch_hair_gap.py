"""Fill the gap in Marie Kratka's hair where the greenhouse shows through.

Her photo was taken in a greenhouse. A strand of hair has fallen away from the
main mass on her left, and through the gap between them you can see a blurred
leaf and some bright glass. rembg reads that gap as part of her -- it is
enclosed by hair on every side -- so the leaf survives into the finished
portrait as a pale green wedge sitting in her hair, which no choice of matte
model avoids: the leaf is in front of her, not behind.

This fills the gap with hair borrowed from further into the same strands, which
is what it would have looked like had the strand fallen a centimetre to the
left. Only pixels the matte already calls "subject", and that are not
hair-coloured, are touched; the leaf keeps its place in the photograph
everywhere else, and everything outside the gap is left byte-for-byte alone.

Run from the top of the repository, through the script environment so that
rembg and OpenCV are on the path:

    ./scripts/make-portraits --python scripts/retouch_hair_gap.py   # if wired up
    scripts/.venv/bin/python scripts/retouch_hair_gap.py

It writes photos/originals/marie_kratka-retouched.jpg, which is what
portraits.toml names as her source. The photo as it was supplied stays at
photos/originals/marie_kratka.jpg and is not modified.
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import portraits

SOURCE = Path("photos/originals/marie_kratka.jpg")
TARGET = Path("photos/originals/marie_kratka-retouched.jpg")

# The left of her hair, comfortably around the gap and clear of her face.
ROI = (1020, 1520, 1250, 2100)  # x0, x1, y0, y1
# Hair strands here run close to vertical, so hair from the same rows this much
# further into the mass carries the right direction and the right tone.
BORROW = 150
MIN_AREA = 1000  # ignore specks: highlights on hair that is really there
CLOSE, DILATE, FEATHER, ROUNDS = 15, 25, 31, 3
QUALITY = 95


def hair_test(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split a tile into hair and not-hair.

    Her hair is warm -- red well above blue. The leaf is green, and the
    glasshouse seen through the gap is bright and neutral. Neither is hair.
    """
    v = rgb.astype(np.int16)
    red, green, blue = v[..., 0], v[..., 1], v[..., 2]
    luminance = (red + green + blue) / 3
    not_hair = (green > np.maximum(red, blue)) | ((luminance > 150) & (red - blue < 30))
    return ~not_hair, not_hair


def main() -> None:
    photo = portraits.load_photo(SOURCE)
    image = np.array(photo.convert("RGB"))
    # The same matte the portrait itself is cut with, so "inside" here means
    # exactly what it will mean when the portrait is made.
    alpha = np.array(portraits.cut_out_person(photo).split()[-1])

    x0, x1, y0, y1 = ROI
    inside = alpha[y0:y1, x0:x1] > 0
    work = image[y0:y1, x0:x1].astype(np.float32)

    for round_no in range(1, ROUNDS + 1):
        current = work.round().astype(np.uint8)
        hairlike, not_hair = hair_test(current)
        mask = (inside & not_hair).astype(np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((CLOSE, CLOSE), np.uint8))

        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        kept = np.zeros_like(mask)
        blobs = 0
        for index in range(1, count):
            if stats[index, 4] >= MIN_AREA:
                kept[labels == index] = 1
                blobs += 1
        if not blobs:
            print(f"round {round_no}: nothing left to fill")
            break
        mask = cv2.dilate(kept, np.ones((DILATE, DILATE), np.uint8))

        # Tone comes from the hair ringing the gap, not from the hair the
        # texture was borrowed from, which sits deeper in and reads darker.
        ring = cv2.dilate(mask, np.ones((81, 81), np.uint8)) & (1 - mask)
        reference = ring.astype(bool) & hairlike & inside
        patch = image[y0:y1, x0 + BORROW : x1 + BORROW].astype(np.float32)
        gain = current[reference].mean(axis=0) / np.clip(
            patch[mask.astype(bool)].mean(axis=0), 1, None
        )
        patch = np.clip(patch * gain, 0, 255)

        feather = cv2.GaussianBlur(
            mask.astype(np.float32) * 255, (FEATHER, FEATHER), 0
        )[..., None] / 255.0
        work = work * (1 - feather) + patch * feather
        print(f"round {round_no}: {blobs} blob(s), {int(mask.sum())} px, gain {gain.round(3)}")

    out = image.copy()
    out[y0:y1, x0:x1] = work.round().astype(np.uint8)

    changed = (out != image).any(axis=2)
    outside = np.ones(image.shape[:2], bool)
    outside[y0:y1, x0:x1] = False
    assert not changed[outside].any(), "the edit escaped its region"
    print(f"changed {int(changed.sum())} px = {100 * changed.mean():.3f}% of the photo")

    Image.fromarray(out).save(TARGET, "JPEG", quality=QUALITY, subsampling=0)
    print("wrote", TARGET)


if __name__ == "__main__":
    main()
