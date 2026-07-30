#!/usr/bin/env python3
"""Turn ordinary photos into the round 200x200 member portraits the site uses.

Run this through ``./scripts/make-portraits``, which creates the virtualenv and
installs the dependencies first.

Pipeline, per photo::

    photos/inbox/linnea_smeds.jpg
      -> honour EXIF rotation (phone photos are usually stored sideways)
      -> rembg: cut the person out of the background
      -> composite onto one flat colour, so every portrait matches
      -> find the face, take a square crop around it
      -> scale to 200x200
      -> apply a soft-edged circular alpha mask
    static/img/member/linnea_smeds.png

The output name comes from the input filename, so name the photo after the
member id used in ``content/member/<id>.md``.
"""

import math

import click
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps

# --- Look of the finished portrait -------------------------------------------

SIZE = 200
BACKGROUND = (245, 245, 245)  # flat colour placed behind the cut-out person
CROP_SCALE = 2.0  # square crop side, as a multiple of the detected face width
CROP_DROP = 0.05  # nudge the crop down slightly, so hair is not clipped
ALPHA_FLOOR = 26  # below this, rembg alpha is background haze rather than a real edge

# The existing portraits have a circle that fades out over roughly six pixels
# rather than a hard edge. Reproduced by insetting the circle and blurring it.
FEATHER = 1.8
INSET = 2.0
SUPERSAMPLE = 4  # mask is drawn this much larger, then shrunk, to anti-alias it

# Ordered least to most permissive. alt_tree yields the fewest false positives
# but misses more faces; default catches the most but is the noisiest.
CASCADES = (
    "haarcascade_frontalface_alt_tree.xml",
    "haarcascade_frontalface_alt2.xml",
    "haarcascade_frontalface_alt.xml",
    "haarcascade_frontalface_default.xml",
)

# Face alignment: rotate so the eyes sit level. The eyeglasses variant is tried
# first because it also handles bare eyes, just more conservatively.
EYE_CASCADES = (
    "haarcascade_eye_tree_eyeglasses.xml",
    "haarcascade_eye.xml",
)
MIN_ALIGN_ANGLE = 0.75  # below this a rotation is not worth the resampling
MAX_ALIGN_ANGLE = 35.0  # beyond this the eye detection is more likely wrong than the head

# macOS resource forks and other dotfiles that are not really photos.
IGNORED_PREFIXES = ("._", ".")
PHOTO_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"})


class SkipPhoto(Exception):
    """A photo could not be processed, with a reason the operator can act on."""


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_photo(path: Path) -> Image.Image:
    """Read a photo, applying the rotation the camera recorded in EXIF.

    Phone cameras store orientation as metadata instead of rotating the pixels.
    Without this, portrait-orientation photos arrive on their side and no face
    is found.
    """
    # Opening the file is the authoritative test of whether it is a usable
    # image; there is no cheap precondition that answers the same question.
    try:
        image = Image.open(path)
    except (OSError, ValueError) as exc:
        raise SkipPhoto(f"could not read the file ({exc})") from exc

    return ImageOps.exif_transpose(image).convert("RGBA")


def cut_out_person(image: Image.Image) -> Image.Image:
    """Replace the background with transparency using rembg."""
    # Imported here rather than at module level so that --keep-background still
    # works when rembg (a ~180MB install) is absent or broken.
    from rembg import remove

    cut = remove(image)

    # rembg leaves a haze of very low alpha across the background it discarded --
    # typically 15% of the frame at alpha 1-10. Invisible against transparency,
    # but once composited onto a flat colour it tints the whole backdrop and
    # leaves ghosts of whatever was behind the subject. Anything this faint is
    # discarded outright; genuine edge feathering sits well above the floor.
    red, green, blue, alpha = cut.split()
    alpha = alpha.point(lambda value: 0 if value < ALPHA_FLOOR else value)
    return Image.merge("RGBA", (red, green, blue, alpha))


def flatten(image: Image.Image, colour: tuple[int, int, int]) -> Image.Image:
    """Composite onto a solid background.

    Needed even for photos with no transparency: the circular mask applied later
    replaces the alpha channel outright, so transparent pixels left here would
    otherwise resurface as black.
    """
    canvas = Image.new("RGBA", image.size, (*colour, 255))
    canvas.alpha_composite(image)
    return canvas.convert("RGB")


def find_face(image: Image.Image) -> tuple[int, int, int, int]:
    """Return the largest detected face as ``(x, y, width, height)``."""
    grey = cv2.equalizeHist(cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY))

    # A portrait subject fills a good part of the frame. Setting a floor also
    # discards faces in the background and speeds detection up considerably.
    smallest = max(40, min(image.size) // 12)

    for name in CASCADES:
        classifier = cv2.CascadeClassifier(cv2.data.haarcascades + name)
        if classifier.empty():
            continue
        faces = classifier.detectMultiScale(
            grey, scaleFactor=1.1, minNeighbors=5, minSize=(smallest, smallest)
        )
        if len(faces) > 0:
            # More than one face is common (someone in the background); the
            # largest is nearly always the subject.
            x, y, width, height = max(faces, key=lambda face: face[2] * face[3])
            return int(x), int(y), int(width), int(height)

    raise SkipPhoto(
        "no face detected. Use a photo where the face is larger, front-on and "
        "in focus, or crop it square yourself and pass --no-detect."
    )


def eye_angle(image: Image.Image, face: tuple[int, int, int, int]) -> float | None:
    """Angle of the line between the eyes, in degrees, or None if not measurable.

    Positive means the subject's head is tilted clockwise on screen (their right
    eye sits lower), which is corrected by rotating the image anticlockwise.
    """
    x, y, width, height = face
    # Eyes are in the upper part of the face box. Restricting the search there
    # keeps nostrils and mouth corners from being mistaken for eyes.
    roi = image.crop((x, y, x + width, y + int(height * 0.6)))
    grey = cv2.equalizeHist(cv2.cvtColor(np.array(roi), cv2.COLOR_RGB2GRAY))
    smallest = max(12, width // 12)

    for name in EYE_CASCADES:
        classifier = cv2.CascadeClassifier(cv2.data.haarcascades + name)
        if classifier.empty():
            continue
        eyes = classifier.detectMultiScale(
            grey, scaleFactor=1.1, minNeighbors=6, minSize=(smallest, smallest)
        )
        if len(eyes) < 2:
            continue

        # Keep the two strongest detections, then order them left to right.
        left, right = sorted(sorted(eyes, key=lambda e: e[2] * e[3])[-2:], key=lambda e: e[0])
        left_x, left_y = left[0] + left[2] / 2, left[1] + left[3] / 2
        right_x, right_y = right[0] + right[2] / 2, right[1] + right[3] / 2

        # Two boxes on top of each other are one eye found twice, not a pair.
        if right_x - left_x < width * 0.15:
            continue

        return math.degrees(math.atan2(right_y - left_y, right_x - left_x))

    return None


def level_eyes(
    image: Image.Image, face: tuple[int, int, int, int], background: tuple[int, int, int]
) -> Image.Image | None:
    """Rotate the photo so the eyes are horizontal. None when no rotation applies."""
    angle = eye_angle(image, face)
    if angle is None or not MIN_ALIGN_ANGLE <= abs(angle) <= MAX_ALIGN_ANGLE:
        return None
    # expand=True so no part of the head is rotated out of frame; the corners
    # this opens up are filled with the same flat colour as the background.
    return image.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=background)


def crop_to_face(image: Image.Image, face: tuple[int, int, int, int]) -> Image.Image:
    """Crop a square around the face, always square and always within the photo."""
    image_width, image_height = image.size
    x, y, width, height = face

    # Never ask for more than the photo can give: a clipped crop would stop
    # being square and the final resize would stretch the face.
    side = max(1, min(int(width * CROP_SCALE), image_width, image_height))

    left = x + width // 2 - side // 2
    top = int(y + height // 2 + side * CROP_DROP) - side // 2

    # Slide the square back inside the photo rather than shrinking it.
    left = max(0, min(left, image_width - side))
    top = max(0, min(top, image_height - side))

    return image.crop((left, top, left + side, top + side))


def crop_centre(image: Image.Image) -> Image.Image:
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    return image.crop((left, top, left + side, top + side))


def circular_mask(size: int) -> Image.Image:
    """A circle with a soft edge, matching the site's existing portraits."""
    big = size * SUPERSAMPLE
    inset = INSET * SUPERSAMPLE
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((inset, inset, big - 1 - inset, big - 1 - inset), fill=255)
    return mask.resize((size, size), Image.LANCZOS).filter(
        ImageFilter.GaussianBlur(radius=FEATHER)
    )


def make_portrait(
    path: Path,
    *,
    remove_background: bool,
    detect_face: bool,
    align: bool,
    background: tuple[int, int, int],
) -> Image.Image:
    image = load_photo(path)
    if remove_background:
        image = cut_out_person(image)

    flat = flatten(image, background)
    if detect_face:
        face = find_face(flat)
        if align:
            levelled = level_eyes(flat, face, background)
            if levelled is not None:
                # The rotation moved everything, so locate the face again rather
                # than trying to transform the old coordinates.
                flat = levelled
                face = find_face(flat)
        framed = crop_to_face(flat, face)
    else:
        framed = crop_centre(flat)

    portrait = framed.resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA")
    portrait.putalpha(circular_mask(SIZE))
    return portrait


def parse_colour(ctx: click.Context, param: click.Parameter, value: str) -> tuple[int, int, int]:
    text = value.removeprefix("#")
    if len(text) != 6 or any(character not in "0123456789abcdefABCDEF" for character in text):
        raise click.BadParameter("colour must look like #f5f5f5")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def collect_photos(inbox: Path) -> list[Path]:
    if not inbox.is_dir():
        return []
    return sorted(
        path
        for path in inbox.iterdir()
        if path.is_file()
        and path.suffix.lower() in PHOTO_SUFFIXES
        and not path.name.startswith(IGNORED_PREFIXES)
    )


def describe(path: Path) -> str:
    """Show a repo-relative path when possible, an absolute one otherwise."""
    resolved = path.resolve()
    root = repo_root()
    return str(resolved.relative_to(root)) if resolved.is_relative_to(root) else str(resolved)


@click.command()
@click.argument(
    "photos",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--inbox",
    type=click.Path(file_okay=False, path_type=Path),
    help="Folder of photos to process  [default: photos/inbox]",
)
@click.option(
    "--out",
    type=click.Path(file_okay=False, path_type=Path),
    help="Where finished portraits are written  [default: static/img/member]",
)
@click.option(
    "--keep-background",
    is_flag=True,
    help="Leave the photo's own background instead of cutting the person out.",
)
@click.option(
    "--no-detect",
    is_flag=True,
    help="Skip face detection and centre-crop instead.",
)
@click.option(
    "--no-align",
    is_flag=True,
    help="Do not rotate the photo to level the subject's eyes.",
)
@click.option(
    "--background",
    default="#f5f5f5",
    callback=parse_colour,
    metavar="#RRGGBB",
    help="Flat colour placed behind the person.",
)
@click.option("--force", is_flag=True, help="Replace portraits that already exist.")
def main(
    photos: tuple[Path, ...],
    inbox: Path | None,
    out: Path | None,
    keep_background: bool,
    no_detect: bool,
    no_align: bool,
    background: tuple[int, int, int],
    force: bool,
) -> None:
    """Turn photos into the round member portraits used on the site.

    With no arguments, processes everything in photos/inbox/. Name each photo
    after the member, e.g. linnea_smeds.jpg for content/member/linnea_smeds.md.
    """
    inbox = inbox or repo_root() / "photos" / "inbox"
    out = out or repo_root() / "static" / "img" / "member"

    selected = sorted(photos) if photos else collect_photos(inbox)
    if not selected:
        click.echo(f"Nothing to do: no photos found in {describe(inbox)}/")
        click.echo(
            "Copy a photo there named after the member, e.g. linnea_smeds.jpg, "
            "then run this again."
        )
        return

    out.mkdir(parents=True, exist_ok=True)
    processed: list[str] = []
    skipped: list[tuple[str, str]] = []

    for path in selected:
        # content/member/<id>.md expects the portrait to be <id>.png
        destination = out / f"{path.stem}.png"
        if destination.exists() and not force:
            reason = f"{destination.name} already exists. Re-run with --force to replace it."
            skipped.append((path.name, reason))
            continue
        try:
            portrait = make_portrait(
                path,
                remove_background=not keep_background,
                detect_face=not no_detect,
                align=not no_align,
                background=background,
            )
        except SkipPhoto as exc:
            skipped.append((path.name, str(exc)))
            continue
        except ImportError:
            raise click.ClickException(
                "rembg is not installed. Re-run ./scripts/make-portraits, or pass "
                "--keep-background to skip background removal."
            ) from None
        portrait.save(destination, "PNG", optimize=True)
        processed.append(f"{path.name} -> {describe(destination)}")

    for line in processed:
        click.echo(f"  {click.style('OK', fg='green')}      {line}")
    for name, reason in skipped:
        click.echo(f"  {click.style('SKIPPED', fg='yellow')} {name}")
        click.echo(f"            {reason}")

    click.echo(f"\nprocessed {len(processed)}, skipped {len(skipped)}")
    if processed:
        click.echo("\nCheck the portraits look right, then commit them:")
        click.echo("  git add static/img/member && git commit -m 'update member portraits'")
    if skipped:
        raise SystemExit(1)


if __name__ == "__main__":
    # Name the wrapper, not this file: that is what people actually type.
    main(prog_name="./scripts/make-portraits")
