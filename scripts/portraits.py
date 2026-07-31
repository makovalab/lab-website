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
import tomllib

import click
from click.core import ParameterSource
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps

# --- Look of the finished portrait -------------------------------------------

SIZE = 200
# Flat colour behind the cut-out person. #d3d3d3, matching the backdrop the
# earlier pipeline produced -- huiqing_zeng, hana_palova, karol_pal, jacob_sieg,
# saswat_mohanty, byung_june, edmundo and lauren_heverly all store exactly this.
BACKGROUND = (211, 211, 211)
FACE_CENTRE_HEIGHT = 0.50  # where the face-box centre sits when the eyes were not found
# Background removal model. u2net_human_seg is trained on people rather than
# general objects and is the same size as the default u2net, so it is a free
# improvement: on a hard photo it stopped attaching a patch of sunlit wall to
# the subject's hair. birefnet-portrait is cleaner still on wispy edges but is
# a 928MB download rather than 168MB, so it is opt-in via --model.
MATTE_MODEL = "u2net_human_seg"
DEFRINGE_WIDTH = 0.004     # boundary band width, as a fraction of the image
DEFRINGE_STRENGTH = 0.8    # how far edge colour is pulled toward the subject's own
STRAY_MARGIN = 8           # lightness above the subject's brightest before a fleck is painted out
UNION_MAX_FRACTION = 0.02  # a recovered piece bigger than this is another object, not a body part
MATTE_SHRINK = 0.004  # erode the cut-out edge by this fraction of the image
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
# Eye-normalised framing: the eyes land on the same two pixels in every
# portrait, so a set of unrelated photos reads as one sitting.
# Measured from the portraits already on the site: median eye distance 0.198 of
# the width, eyes 45% down. That corresponds to a head height of roughly 71% of
# the frame (inter-pupil distance is about 0.28 of crown-to-chin), which is the
# range passport standards specify and what portrait practice recommends.
# Nudged slightly wider and lower than the median so no crown is clipped.
EYE_DISTANCE = 0.19   # kept for reference; scaling now uses head height
EYE_HEIGHT = 0.46     # how far down the frame the eyes sit

# Head-size normalisation: every portrait shows a head this tall, as a fraction
# of the output. Passport standards put the head at 70-80% of the frame; a
# little less suits a round crop, which trims the corners anyway.
HEAD_HEIGHT = 0.62
HEAD_CENTRE_HEIGHT = 0.48  # where the middle of the head sits, when eyes are unknown
HEAD_CENTRE_BLEND = 0.5    # 0 = centre on the eyes, 1 = centre on the head silhouette

# Two-stage downscaling: below this scale, pre-shrink with a proper filter
# first, leaving the warp only this much scaling to do.
PREFILTER_BELOW = 0.8
PREFILTER_TARGET = 0.8

YUNET_CONFIDENCE = 0.6  # detection score below which a face is not trusted

# Lighting normalisation targets, in LAB lightness (0-255).
TARGET_LIGHTNESS = 144.0  # median lightness of the face, measured across the site
TARGET_SPREAD = 133.0     # 10th-to-90th percentile spread, i.e. contrast
LIGHTING_STRENGTH = 0.7   # apply only part of the correction

MAX_ALIGN_ANGLE = 35.0  # beyond this the eye detection is more likely wrong than the head

# macOS resource forks and other dotfiles that are not really photos.
IGNORED_PREFIXES = ("._", ".")
PHOTO_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"})


class SkipPhoto(Exception):
    """A photo could not be processed, with a reason the operator can act on."""


def load_registry() -> dict[str, dict]:
    """Per-person overrides from scripts/portraits.toml, if it exists.

    Some photos need a different setting from the rest, and the reason is never
    obvious from the photo alone. Recording it here means a later regeneration
    reproduces what was approved instead of rediscovering the same problems.
    """
    path = Path(__file__).resolve().parent / "portraits.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


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


def keep_largest_region(matte: np.ndarray) -> np.ndarray:
    """Zero everything except the largest connected blob in the matte."""
    solid = (matte > 128).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(solid, connectivity=8)
    if count <= 2:  # background plus at most one region: nothing to discard
        return matte
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.where(labels == largest, matte, 0)


def shrink_matte(matte: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Erode the matte by a fraction of the image size, to shed contaminated edges."""
    radius = max(1, round(min(size) * MATTE_SHRINK))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
    return cv2.erode(matte.astype(np.uint8), kernel).astype(matte.dtype)


def union_small_regions(primary: np.ndarray, secondary: np.ndarray) -> np.ndarray:
    """Add back small pieces the secondary model kept and the primary dropped.

    No single model gets every photo right. On one of these, birefnet correctly
    excludes a second person standing behind the subject but also mattes away
    the subject's ear; u2net_human_seg keeps the ear but keeps the stranger too.
    Size tells them apart -- an ear is a couple of thousand pixels, a whole
    person is a hundred thousand -- so only small additions are accepted.
    """
    extra = (secondary > 128) & (primary <= 128)
    if not extra.any():
        return primary

    limit = UNION_MAX_FRACTION * primary.size
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        extra.astype(np.uint8), connectivity=8
    )
    keep = np.zeros_like(extra)
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] <= limit:
            keep |= labels == index

    return np.where(keep, secondary, primary)


def cut_out_person(
    image: Image.Image, model: str = MATTE_MODEL, union_model: str | None = None
) -> Image.Image:
    """Replace the background with transparency using rembg."""
    # Imported here rather than at module level so that --keep-background still
    # works when rembg (a ~180MB install) is absent or broken.
    from rembg import new_session, remove

    # Hand rembg the image exactly as it is, alpha included. Compositing onto an
    # opaque colour first sounds safer but measurably is not: on a source that
    # was itself a circular crop, backing it with a flat colour made rembg keep
    # 76% of the frame as "subject" instead of 45%, because the disc then reads
    # as the object. For an ordinary opaque photo the two are identical.
    matte = np.array(remove(image, session=new_session(model)).split()[-1])
    if union_model:
        second = np.array(remove(image, session=new_session(union_model)).split()[-1])
        matte = union_small_regions(matte, second)
    matte = matte.astype(np.uint16)

    # rembg leaves a haze of very low alpha across the background it discarded --
    # typically 15% of the frame at alpha 1-10. Invisible against transparency,
    # but once composited onto a flat colour it tints the whole backdrop and
    # leaves ghosts of whatever was behind the subject. Anything this faint is
    # discarded outright; genuine edge feathering sits well above the floor.
    matte[matte < ALPHA_FLOOR] = 0

    # Drop anything not joined to the main subject. rembg sometimes keeps a
    # stray patch of background -- a bright piece of wall, a bag on a chair --
    # which then floats in the finished portrait with nothing attached to it.
    matte = keep_largest_region(matte)

    # Pull the edge in slightly. Pixels on the boundary are a blend of subject
    # and whatever was behind them, and that colour is baked into their RGB; on
    # a sunlit background it shows up as a warm fringe once the person is moved
    # onto a neutral backdrop. Discarding the outermost pixels is cruder than
    # solving for the true foreground colour, but it is reliable and leaves no
    # halo behind.
    matte = shrink_matte(matte, image.size)

    # Respect transparency the source already had: a pixel is only kept if both
    # the original and rembg consider it part of the picture.
    original = np.array(image.split()[-1]).astype(np.uint16)
    combined = (matte * original // 255).astype(np.uint8)

    red, green, blue, _ = image.split()
    return Image.merge("RGBA", (red, green, blue, Image.fromarray(combined, "L")))


def defringe(image: Image.Image) -> Image.Image:
    """Neutralise colour picked up from the old background at the cut-out edge.

    Boundary pixels are a blend of subject and whatever was behind them, and
    that colour is baked into their RGB -- a sunlit wall leaves a warm rim along
    the hair which looks wrong once the person is on a neutral backdrop. Their
    colour is pulled back towards the subject's own palette while their
    lightness is left alone, so the shape of the hair survives and only the
    contamination goes.
    """
    array = np.array(image)
    alpha = array[:, :, 3].copy()
    solid = (alpha > 128).astype(np.uint8)

    radius = max(1, round(min(image.size) * DEFRINGE_WIDTH))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
    band = (cv2.dilate(solid, kernel) - cv2.erode(solid, kernel)).astype(bool)
    interior = cv2.erode(solid, kernel).astype(bool)
    if not band.any() or not interior.any():
        return image

    lab = cv2.cvtColor(array[:, :, :3], cv2.COLOR_RGB2LAB).astype(np.float32)
    # The subject's own colour, away from any edge.
    target_a = float(np.median(lab[:, :, 1][interior]))
    target_b = float(np.median(lab[:, :, 2][interior]))

    # Flecks of old background that the matte kept are brighter than anything on
    # the subject -- a gap in the hair, a glimpse of sky past a shoulder.
    # Neutralising their colour only turns a tan speck into a white one, which
    # stands out more. Paint them out from their surroundings instead: cutting
    # their alpha would leave a hole showing the backdrop, which is just as
    # visible.
    ceiling = float(np.percentile(lab[:, :, 0][interior], 99))
    strays = band & (lab[:, :, 0] > ceiling + STRAY_MARGIN)
    # Cutting them is better than painting them out: inpainting samples the very
    # neighbours that are too bright, and measurably left more white than it
    # removed. A cut leaves the backdrop showing, which is darker and quieter.
    alpha = np.where(strays, 0, alpha).astype(np.uint8)
    band = band & ~strays

    for channel, target in ((1, target_a), (2, target_b)):
        lab[:, :, channel][band] += (target - lab[:, :, channel][band]) * DEFRINGE_STRENGTH

    # Write back only the band. Converting RGB -> LAB -> RGB is lossy, so
    # returning the whole round-tripped image would shift every pixel slightly
    # and visibly wash the portrait out, even where nothing was corrected.
    corrected = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB)
    rgb = array[:, :, :3].copy()
    rgb[band] = corrected[band]
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")


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



def yunet_model() -> Path:
    return Path(__file__).resolve().parent / "models" / "face_detection_yunet_2023mar.onnx"


def detect_with_yunet(image: Image.Image):
    """Face box and both eye centres, or None.

    Preferred over the Haar cascades because it returns the eyes directly and,
    being a small neural network rather than a texture matcher, it still finds
    them behind glasses and sunglasses -- which defeated the cascades on 7 of
    this lab's 15 photos.
    """
    model = yunet_model()
    if not model.is_file():
        return None

    frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    detector = cv2.FaceDetectorYN.create(
        str(model), "", (frame.shape[1], frame.shape[0]), YUNET_CONFIDENCE, 0.3, 5000
    )
    _, faces = detector.detect(frame)
    if faces is None or len(faces) == 0:
        return None

    # The largest face is the subject; anyone in the background is smaller.
    best = max(faces, key=lambda row: row[2] * row[3])
    x, y, width, height = (int(v) for v in best[:4])
    # Landmarks are the subject's right eye then left, i.e. left-to-right on
    # screen already, but sort anyway rather than rely on it.
    first, second = (float(best[4]), float(best[5])), (float(best[6]), float(best[7]))
    left, right = sorted((first, second), key=lambda point: point[0])
    return (x, y, width, height), (left, right)


def eye_positions(image: Image.Image, face: tuple[int, int, int, int]):
    """Centres of the two eyes in image coordinates, or None."""
    x, y, width, height = face
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
        left, right = sorted(sorted(eyes, key=lambda e: e[2] * e[3])[-2:], key=lambda e: e[0])
        left_c = (x + left[0] + left[2] / 2, y + left[1] + left[3] / 2)
        right_c = (x + right[0] + right[2] / 2, y + right[1] + right[3] / 2)
        if right_c[0] - left_c[0] < width * 0.15:
            continue
        return left_c, right_c
    return None




def normalise_lighting(
    image: Image.Image, face: tuple[int, int, int, int], strength: float = LIGHTING_STRENGTH
) -> Image.Image:
    """Even out exposure and contrast between photos, judged on the face.

    Works on lightness only, in LAB, so hue and saturation are untouched --
    this corrects how a photo was lit and must not shift anyone's skin tone.
    Statistics come from the face alone, so a dark jumper or a bright window
    cannot drag the correction around. Alpha is carried through unchanged.
    """
    red, green, blue, alpha = image.split()
    lab = cv2.cvtColor(np.array(Image.merge("RGB", (red, green, blue))), cv2.COLOR_RGB2LAB)
    lab = lab.astype(np.float32)
    lightness = lab[:, :, 0]

    x, y, width, height = face
    patch = lightness[max(0, y):y + height, max(0, x):x + width]
    if patch.size < 100:
        return image

    # Percentiles rather than mean/std: robust to a blown highlight or a deep shadow.
    low, mid, high = np.percentile(patch, [10, 50, 90])
    gain = np.clip(TARGET_SPREAD / max(high - low, 1.0), 0.5, 2.0)

    corrected = (lightness - mid) * gain + TARGET_LIGHTNESS
    # Ease off: apply only part of the correction, so a face lit differently
    # still reads as itself rather than as something retouched.
    blended = lightness + (corrected - lightness) * strength
    lab[:, :, 0] = np.clip(blended, 0, 255)

    result = Image.fromarray(cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB))
    result.putalpha(alpha)
    return result


def circular_mask(size: int) -> Image.Image:
    """A circle with a soft edge, matching the site's existing portraits."""
    big = size * SUPERSAMPLE
    inset = INSET * SUPERSAMPLE
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((inset, inset, big - 1 - inset, big - 1 - inset), fill=255)
    return mask.resize((size, size), Image.LANCZOS).filter(
        ImageFilter.GaussianBlur(radius=FEATHER)
    )


def detection_view(cut_out: Image.Image) -> Image.Image:
    """A plain RGB view of the cut-out, purely so the Haar cascades can run.

    Transparent pixels have undefined colour, so they are laid on mid-grey
    first. This image is never used for output.
    """
    canvas = Image.new("RGBA", cut_out.size, (128, 128, 128, 255))
    canvas.alpha_composite(cut_out)
    return canvas.convert("RGB")


def similarity_warp(
    cut_out: Image.Image, centre: tuple[float, float], angle: float, scale: float,
    target: tuple[float, float],
) -> Image.Image:
    """Rotate, scale and translate the cut-out onto a SIZE x SIZE transparent frame.

    The cut-out behaves as though it sits on an infinite transparent canvas:
    anything the frame reaches beyond the original edges comes back transparent
    rather than clipped, so a head near the top of its photo still gets
    headroom.

    Large reductions are done in two stages. warpAffine point-samples, so
    shrinking a 1280px photo to a fifth of its size in one pass aliases badly
    and looks pixelated; PIL's resize filters properly across the pixels it is
    discarding. The warp itself is then left with little or no scaling to do.
    """
    source = cut_out
    if scale < PREFILTER_BELOW:
        width = max(SIZE, round(cut_out.width * scale / PREFILTER_TARGET))
        height = max(SIZE, round(cut_out.height * scale / PREFILTER_TARGET))
        shrink = width / cut_out.width
        source = cut_out.resize((width, height), Image.LANCZOS)
        centre = (centre[0] * shrink, centre[1] * shrink)
        scale /= shrink

    matrix = cv2.getRotationMatrix2D(centre, angle, scale)
    matrix[0, 2] += target[0] - centre[0]
    matrix[1, 2] += target[1] - centre[1]
    warped = cv2.warpAffine(
        np.array(source), matrix, (SIZE, SIZE),
        flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0),
    )
    return Image.fromarray(warped, "RGBA")


def frame_with_eyes(cut_out: Image.Image, face: tuple[int, int, int, int], eyes) -> Image.Image:
    """Level the eyes, then size and place the head the same way for everyone."""
    (left_x, left_y), (right_x, right_y) = eyes

    angle = math.degrees(math.atan2(right_y - left_y, right_x - left_x))
    if abs(angle) > MAX_ALIGN_ANGLE:
        angle = 0.0  # implausible tilt: trust the head measurement, not the eyes

    crown, chin, head_x = head_extent(cut_out, face)
    scale = (HEAD_HEIGHT * SIZE) / max(chin - crown, 1.0)

    # Neither reference works alone. The eye midpoint drifts off the head's
    # centre when someone is turned three-quarters on; the silhouette centre
    # gets pulled sideways by a shoulder. Splitting the difference keeps both
    # errors small: measured across this set it halved the worst offset.
    eye_x = (left_x + right_x) / 2
    centre_x = eye_x * (1 - HEAD_CENTRE_BLEND) + head_x * HEAD_CENTRE_BLEND

    return similarity_warp(
        cut_out,
        centre=(centre_x, (left_y + right_y) / 2),
        angle=angle,
        scale=scale,
        target=(SIZE * 0.5, SIZE * EYE_HEIGHT),
    )


def head_extent(
    cut_out: Image.Image, face: tuple[int, int, int, int]
) -> tuple[float, float, float]:
    """Crown, chin and horizontal centre of the head, in source pixels.

    The alpha matte gives the crown exactly -- it is the topmost pixel of the
    subject in the columns the head occupies -- which no face detector reports,
    since Haar finds eyebrows-to-chin and ignores hair. Scaling on crown-to-chin
    makes every head the same size in the output regardless of hairstyle, pose,
    or whether the eyes could be found at all.
    """
    x, y, width, height = face
    alpha = np.array(cut_out.split()[-1]) > 128

    # Columns the face occupies, widened a little to take in hair at the sides.
    margin = int(width * 0.25)
    left = max(0, x - margin)
    right = min(alpha.shape[1], x + width + margin)
    column_band = alpha[:, left:right]

    rows = np.where(column_band.any(axis=1))[0]
    crown = float(rows[0]) if len(rows) else float(y)

    # Chin: the face box bottom is a good estimate and, unlike the silhouette,
    # is not confused by shoulders or a high collar.
    chin = float(y + height)

    # Horizontal centre from the upper half of the head only. Taking the whole
    # crown-to-chin band lets a visible shoulder drag the centre sideways, which
    # showed up as portraits sitting up to 17px off centre.
    upper = alpha[int(crown):int(crown + (chin - crown) * 0.5), :]
    columns = np.where(upper.any(axis=0))[0]
    centre = float((columns[0] + columns[-1]) / 2) if len(columns) else x + width / 2

    return crown, chin, centre


def head_centre_x(cut_out: Image.Image, face: tuple[int, int, int, int]) -> float:
    """Horizontal centre of the head, taken from the cut-out silhouette.

    The Haar box is a poor guide to where the head actually sits: a beard, a
    fringe or a three-quarter pose all shift it sideways, which then shows up as
    an off-centre portrait. The alpha channel knows exactly how wide the head is
    at eye level, so measure it there instead.
    """
    x, y, width, height = face
    alpha = np.array(cut_out.split()[-1])
    band = alpha[max(0, y):y + height, :]
    columns = np.where((band > 128).any(axis=0))[0]
    if len(columns) == 0:
        return x + width / 2
    return float((columns[0] + columns[-1]) / 2)


def frame_on_face(cut_out: Image.Image, face: tuple[int, int, int, int]) -> Image.Image:
    """Fallback framing when no usable pair of eyes was found.

    Sunglasses, ordinary glasses, a strong profile or a heavy fringe all defeat
    eye detection. The face box is a coarser reference, so the result is less
    consistent between people, but it is always available.
    """
    crown, chin, centre_x = head_extent(cut_out, face)
    scale = (HEAD_HEIGHT * SIZE) / max(chin - crown, 1.0)

    # No eyes to align on, but the head can still be sized and placed the same
    # way, so this route matches the eye route in everything but rotation.
    return similarity_warp(
        cut_out,
        centre=(centre_x, (crown + chin) / 2),
        angle=0.0,
        scale=scale,
        target=(SIZE * 0.5, SIZE * HEAD_CENTRE_HEIGHT),
    )


def lay_on_disc(framed: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    """Put the framed cut-out on the coloured disc and cut the circle out of it.

    Done last, so everything before this point works on transparency and the
    flat colour never has to be rotated, cropped or resampled.
    """
    disc = Image.new("RGBA", (SIZE, SIZE), (*background, 255))
    disc.alpha_composite(framed)
    disc.putalpha(circular_mask(SIZE))
    return disc


def make_portrait(
    path: Path,
    *,
    remove_background: bool,
    defringe_edges: bool = True,
    model: str = MATTE_MODEL,
    union_model: str | None = None,
    detect_face: bool,
    eye_frame: bool,
    lighting: bool,
    lighting_strength: float,
    background: tuple[int, int, int],
) -> tuple[Image.Image, str]:
    image = load_photo(path)
    cut_out = cut_out_person(image, model, union_model) if remove_background else image
    if remove_background and defringe_edges:
        cut_out = defringe(cut_out)

    if not detect_face:
        side = min(cut_out.size)
        left = (cut_out.width - side) // 2
        top = (cut_out.height - side) // 2
        framed = cut_out.crop((left, top, left + side, top + side)).resize(
            (SIZE, SIZE), Image.LANCZOS
        )
        return lay_on_disc(framed, background), "centre"

    view = detection_view(cut_out)
    detected = detect_with_yunet(view) if eye_frame else None

    if detected is not None:
        face, eyes = detected
        route = "eyes"
    else:
        face, eyes = find_face(view), None
        route = "face box"

    if lighting:
        cut_out = normalise_lighting(cut_out, face, lighting_strength)

    if eyes is None and eye_frame:
        # YuNet found nothing; the Haar cascades occasionally still do.
        eyes = eye_positions(view, face)
        if eyes is not None:
            route = "eyes (haar)"

    framed = frame_with_eyes(cut_out, face, eyes) if eyes else frame_on_face(cut_out, face)
    return lay_on_disc(framed, background), route


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
    "--background",
    default="#d3d3d3",
    callback=parse_colour,
    metavar="#RRGGBB",
    help="Flat colour placed behind the person  [default: #d3d3d3]",
)
@click.option(
    "--no-eye-frame",
    is_flag=True,
    help="Frame on the face box instead of normalising on the eyes.",
)
@click.option(
    "--lighting",
    is_flag=True,
    help="Experimental: even out exposure and contrast between photos.",
)
@click.option(
    "--model",
    default=MATTE_MODEL,
    show_default=True,
    help="rembg model for background removal. birefnet-portrait is cleaner on "
         "wispy hair but downloads 928MB instead of 168MB.",
)
@click.option(
    "--no-defringe",
    is_flag=True,
    help="Keep colour the cut-out edge picked up from the old background.",
)
@click.option("--force", is_flag=True, help="Replace portraits that already exist.")
@click.pass_context
def main(
    ctx: click.Context,
    photos: tuple[Path, ...],
    inbox: Path | None,
    out: Path | None,
    keep_background: bool,
    no_detect: bool,
    no_eye_frame: bool,
    lighting: bool,
    background: tuple[int, int, int],
    no_defringe: bool,
    model: str,
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

    registry = load_registry()

    for path in selected:
        # content/member/<id>.md expects the portrait to be <id>.png
        destination = out / f"{path.stem}.png"
        if destination.exists() and not force:
            reason = f"{destination.name} already exists. Re-run with --force to replace it."
            skipped.append((path.name, reason))
            continue

        # Per-person settings, overridden by anything given on the command line.
        entry = registry.get(path.stem, {})
        settings = {
            "remove_background": not entry.get("keep_background", keep_background),
            "detect_face": entry.get("detect", not no_detect),
            "eye_frame": not no_eye_frame,
            "lighting": entry.get("lighting", lighting),
            "lighting_strength": float(entry.get("lighting_strength", LIGHTING_STRENGTH)),
            "defringe_edges": entry.get("defringe", not no_defringe),
            "model": entry.get("model", model),
            "union_model": entry.get("union_model"),
        }
        for name, value in (("model", model), ("lighting", lighting)):
            if ctx.get_parameter_source(name) is ParameterSource.COMMANDLINE:
                settings[name] = value

        try:
            portrait, route = make_portrait(path, background=background, **settings)
        except SkipPhoto as exc:
            skipped.append((path.name, str(exc)))
            continue
        except ImportError:
            raise click.ClickException(
                "rembg is not installed. Re-run ./scripts/make-portraits, or pass "
                "--keep-background to skip background removal."
            ) from None
        portrait.save(destination, "PNG", optimize=True)
        tag = route if path.stem not in registry else f"{route}, registry"
        processed.append(f"{path.name} -> {describe(destination)}  [{tag}]")

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
