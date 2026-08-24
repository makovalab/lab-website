"""Take the leaf out of Marie Kratka's hair.

Her photo was taken in a greenhouse, and a leaf hangs between the camera and the
left side of her hair. Look at the photo closely and her hair runs straight
through behind it: the leaf is a translucent veil over hair that is all there,
not a gap you can see through. rembg does not read it that way. It keeps the
veiled hair as part of her but leaves it green, and where the veil is strongest
it stops recognising hair at all and cuts a bite out of her silhouette. On the
photo's own bright background the bite is invisible; on the flat grey the
portraits use it reads as a chunk taken out of her hair.

Both halves of that are fixed here, and they have to be fixed together -- taking
the green out on its own leaves the bite behind with nothing to disguise it,
which looks worse than the leaf did.

  1. Veil.  Pixels the matte calls "subject" that are not hair-coloured: the
     green cast, and the bright glass where the veil washes hair out.
  2. Bite.  Concavities in the silhouette, found by closing it -- hair rembg
     dropped because the veil hid it.

Both are filled with hair borrowed from further into the same strands, toned to
match the hair ringing the fill rather than the hair the texture came from,
which sits deeper in and reads darker. Filling changes the matte, so it is done
in rounds until nothing is left to fill; in practice one round does it.

Run from the top of the repository, through the script environment so that rembg
and OpenCV are on the path:

    scripts/.venv/bin/python scripts/retouch_hair_gap.py

It writes photos/originals/marie_kratka-retouched.jpg, which is what
portraits.toml names as her source. The photo as it was supplied stays at
photos/originals/marie_kratka.jpg and is never modified.
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import portraits

SOURCE = Path("photos/originals/marie_kratka.jpg")
TARGET = Path("photos/originals/marie_kratka-retouched.jpg")

# The left of her hair, comfortably around the leaf and clear of her face.
ROI = (980, 1560, 1150, 1980)  # x0, x1, y0, y1
# Hair strands here run close to vertical, so hair from the same rows this much
# further into the mass carries the right direction and the right tone.
BORROW = 150
VEIL_MIN = 800  # ignore specks: highlights on hair that is really there
BITE_MIN = 600
# Wide enough to bridge the bite, which is about 85x131. A kernel that fits
# through the opening would leave it alone, which is what smaller ones do.
BITE_KERNEL = 241
CLOSE, DILATE, FEATHER, ROUNDS = 15, 25, 31, 4
QUALITY = 95


def split_hair(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split a tile into hair and not-hair.

    Her hair is warm -- red well above blue. The leaf is green, and where the
    veil is thin the glasshouse behind washes the hair out bright and neutral.
    Neither is hair.
    """
    v = rgb.astype(np.int16)
    red, green, blue = v[..., 0], v[..., 1], v[..., 2]
    luminance = (red + green + blue) / 3
    not_hair = (green > np.maximum(red, blue)) | ((luminance > 150) & (red - blue < 30))
    return ~not_hair, not_hair


def largest_blobs(mask: np.ndarray, minimum: int) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    kept = np.zeros_like(mask)
    for index in range(1, count):
        if stats[index, 4] >= minimum:
            kept[labels == index] = 1
    return kept


def main() -> None:
    image = np.array(portraits.load_photo(SOURCE).convert("RGB"))
    x0, x1, y0, y1 = ROI
    work = image[y0:y1, x0:x1].astype(np.float32)
    whole = image.copy()

    for round_no in range(1, ROUNDS + 1):
        whole[y0:y1, x0:x1] = work.round().astype(np.uint8)
        # The same matte the portrait itself is cut with, re-read each round
        # because filling hair in changes where rembg puts her edge.
        matte = portraits.cut_out_person(Image.fromarray(whole).convert("RGBA"))
        inside = np.array(matte.split()[-1])[y0:y1, x0:x1] > 0
        current = work.round().astype(np.uint8)
        hairlike, not_hair = split_hair(current)

        veil = (inside & not_hair).astype(np.uint8)
        veil = cv2.morphologyEx(veil, cv2.MORPH_CLOSE, np.ones((CLOSE, CLOSE), np.uint8))
        veil = largest_blobs(veil, VEIL_MIN)

        solid = inside.astype(np.uint8)
        closed = cv2.morphologyEx(
            solid,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (BITE_KERNEL, BITE_KERNEL)),
        )
        bite = largest_blobs(closed & (1 - solid), BITE_MIN)

        print(f"round {round_no}: veil {int(veil.sum())} px, bite {int(bite.sum())} px")
        mask = ((veil | bite) > 0).astype(np.uint8)
        if not mask.any():
            break
        mask = cv2.dilate(mask, np.ones((DILATE, DILATE), np.uint8))

        ring = cv2.dilate(mask, np.ones((81, 81), np.uint8)) & (1 - mask)
        reference = ring.astype(bool) & hairlike & inside
        if reference.sum() < 500:  # nearly all of the ring is fill: widen it
            reference = ring.astype(bool) & hairlike
        patch = image[y0:y1, x0 + BORROW : x1 + BORROW].astype(np.float32)
        gain = current[reference].mean(axis=0) / np.clip(
            patch[mask.astype(bool)].mean(axis=0), 1, None
        )
        patch = np.clip(patch * gain, 0, 255)

        feather = cv2.GaussianBlur(
            mask.astype(np.float32) * 255, (FEATHER, FEATHER), 0
        )[..., None] / 255.0
        work = work * (1 - feather) + patch * feather

    whole[y0:y1, x0:x1] = work.round().astype(np.uint8)

    changed = (whole != image).any(axis=2)
    outside = np.ones(image.shape[:2], bool)
    outside[y0:y1, x0:x1] = False
    assert not changed[outside].any(), "the edit escaped its region"
    print(f"changed {int(changed.sum())} px = {100 * changed.mean():.3f}% of the photo")

    Image.fromarray(whole).save(TARGET, "JPEG", quality=QUALITY, subsampling=0)
    print("wrote", TARGET)


if __name__ == "__main__":
    main()
