"""Tests for the parts of portraits.py that decide how a portrait is framed.

These deliberately avoid the background-removal model: it is a 168MB download
and a slow run, and none of what is checked here depends on it. Everything
below works on synthetic images, so the suite finishes in about a second.

What is being protected is the claim the constants at the top of portraits.py
make -- that every measurement is a fraction of SIZE, so the same photo yields
the same framing whatever size it is made at. That claim is easy to break by
adding a constant in pixels, and the result is portraits that no longer look
like one sitting when the page scales them into the same slot.

    ./scripts/make-portraits --test
"""

from __future__ import annotations

import numpy as np
import portraits
import pytest
from PIL import Image, ImageDraw


@pytest.fixture(autouse=True)
def restore_size():
    """SIZE is module state the pipeline writes; put it back after each test."""
    original = portraits.SIZE
    yield
    portraits.SIZE = original


def falloff(mask: Image.Image) -> float:
    """Width of the circle's soft edge, as a fraction of the image edge.

    Measured radially rather than along a row, because the disc runs to the
    frame edge and a single row barely crosses it.
    """
    alpha = np.asarray(mask, dtype=float) / 255
    size = alpha.shape[0]
    centre = (size - 1) / 2
    y, x = np.mgrid[0:size, 0:size]
    radius = np.sqrt((x - centre) ** 2 + (y - centre) ** 2) / size

    order = np.argsort(radius, axis=None)
    radii = radius.flatten()[order]
    values = alpha.flatten()[order]
    # radius at which the edge has faded to 90% and to 10%
    outer = np.interp(-0.1, -values, radii)
    inner = np.interp(-0.9, -values, radii)
    return outer - inner


def person(size: int, head_px: int) -> tuple[Image.Image, tuple[int, int, int, int], tuple]:
    """A synthetic cut-out: a head on transparency, with known eyes.

    Enough for the framing maths, which only ever looks at the alpha channel
    and the coordinates it is handed.

    head_extent takes the crown from the topmost opaque pixel but the chin from
    the bottom of the face box, so the box has to end at the chin here the way a
    real detection does. A box ending anywhere else silently changes the head
    height every assertion below is written against.
    """
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    centre_x, crown = size // 2, size // 4
    half = head_px // 3
    draw.ellipse((centre_x - half, crown, centre_x + half, crown + head_px),
                 fill=(180, 150, 130, 255))
    eye_y = crown + int(head_px * 0.45)
    eyes = ((centre_x - half // 2, eye_y), (centre_x + half // 2, eye_y))
    # box top at the brow, bottom at the chin -- roughly what Haar and YuNet give
    brow = crown + head_px // 4
    face = (centre_x - half, brow, 2 * half, crown + head_px - brow)
    return image, face, eyes


# --- the size ladder ---------------------------------------------------------

@pytest.mark.parametrize("head_px, expected", [
    (1216, 600),   # a full-frame phone photo, far past what 600 needs
    (372, 600),    # exactly 0.62 * 600
    (371, 400),    # one pixel short of 600
    (312, 400),    # edmundo
    (248, 400),    # exactly 0.62 * 400
    (247, 200),
    (124, 200),
    (20, 200),     # far too small for any of them: still the smallest, not zero
])
def test_size_for_head_picks_largest_it_fills(head_px, expected):
    assert portraits.size_for_head(head_px) == expected


def test_size_for_head_never_enlarges():
    """The chosen size must not ask for more head than the photo has."""
    for head_px in range(60, 1400, 7):
        chosen = portraits.size_for_head(head_px)
        if chosen > min(portraits.SIZE_LADDER):
            assert portraits.HEAD_HEIGHT * chosen <= head_px


# --- framing is the same shape at every size ---------------------------------

@pytest.mark.parametrize("size", portraits.SIZE_LADDER)
def test_eyes_land_in_the_same_place_at_every_size(size):
    """The whole point of the eye framing: one sitting, whatever the size."""
    portraits.SIZE = size
    cut_out, face, eyes = person(1200, head_px=600)

    framed = portraits.frame_with_eyes(cut_out, face, eyes)

    assert framed.size == (size, size)
    # Thresholded the way head_extent does it: counting the faint antialiased
    # fringe as head adds a pixel or two per edge, which is a larger share of a
    # 200px portrait than a 600px one and would read as a size-dependent result.
    alpha = np.asarray(framed)[:, :, 3] > 128
    rows = np.nonzero(alpha.any(axis=1))[0]
    columns = np.nonzero(alpha.any(axis=0))[0]
    head_height = (rows[-1] - rows[0]) / size
    centre_x = (columns[0] + columns[-1]) / 2 / size

    assert head_height == pytest.approx(portraits.HEAD_HEIGHT, abs=0.02)
    assert centre_x == pytest.approx(0.5, abs=0.02)


def test_framing_is_identical_once_scaled_to_a_common_size():
    """A 600px portrait shrunk to 200 should match one made at 200."""
    cut_out, face, eyes = person(1200, head_px=600)

    portraits.SIZE = 200
    small = portraits.frame_with_eyes(cut_out, face, eyes)
    portraits.SIZE = 600
    large = portraits.frame_with_eyes(cut_out, face, eyes).resize((200, 200), Image.LANCZOS)

    difference = np.abs(
        np.asarray(small, dtype=float)[:, :, 3] - np.asarray(large, dtype=float)[:, :, 3]
    )
    # Resampling alone moves edge pixels, so compare the shape, not every pixel.
    assert difference.mean() < 6


# --- the soft edge of the disc ----------------------------------------------

def test_circular_mask_edge_is_the_same_softness_at_every_size():
    """FEATHER and INSET are fractions; in pixels the 600s would look harder.

    The page scales every portrait into the same slot, so an edge that is
    relatively tighter at 600 reads as a harder, more aliased circle beside its
    200px neighbours.
    """
    widths = {size: falloff(portraits.circular_mask(size)) for size in portraits.SIZE_LADDER}
    assert max(widths.values()) - min(widths.values()) < 0.005, widths


@pytest.mark.parametrize("size", portraits.SIZE_LADDER)
def test_circular_mask_is_opaque_in_the_middle_and_clear_in_the_corner(size):
    mask = np.asarray(portraits.circular_mask(size))
    assert mask[size // 2, size // 2] == 255
    assert mask[0, 0] == 0


# --- continuing a subject the photo cuts off ---------------------------------

def torso(size: int, reaches_bottom: bool) -> Image.Image:
    """A shirt-shaped block that either runs off the bottom edge or stops short."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bottom = size if reaches_bottom else int(size * 0.7)
    ImageDraw.Draw(image).rectangle(
        (int(size * 0.2), int(size * 0.3), int(size * 0.8), bottom - 1),
        fill=(120, 40, 60, 255),
    )
    return image


def test_subject_running_off_the_bottom_is_carried_on():
    cut_out = torso(200, reaches_bottom=True)

    extended = portraits.extend_below(cut_out)

    assert extended.height > cut_out.height
    # the shirt continues rather than stopping at the old edge
    alpha = np.asarray(extended)[:, :, 3]
    assert (alpha[cut_out.height + 10] > 128).any()


def test_subject_that_ends_inside_the_frame_is_left_alone():
    """Nothing to continue: the photo already shows where the person stops."""
    cut_out = torso(200, reaches_bottom=False)

    assert portraits.extend_below(cut_out).size == cut_out.size


def test_extending_does_not_move_anything_already_measured():
    """Padding only the bottom keeps the origin, so face and eye coords hold.

    The photograph itself is left alone apart from a few rows right at the cut,
    which are painted over on purpose: they are the matte's own boundary and
    still carry whatever was behind the subject.
    """
    cut_out = torso(200, reaches_bottom=True)

    extended = portraits.extend_below(cut_out)

    assert extended.width == cut_out.width
    seam = max(1, round(cut_out.height * portraits.TORSO_SEAM))
    untouched = cut_out.height - seam - 1
    assert np.array_equal(
        np.asarray(cut_out)[:untouched], np.asarray(extended)[:untouched]
    )


def round_torso(size: int) -> tuple[Image.Image, np.ndarray]:
    """A shirt cut off by a circular photo edge rather than a straight one.

    Two of the sources are themselves round crops lifted off an old version of
    the site, so what truncates the subject is an arc part-way up the frame.
    """
    extent = Image.new("L", (size, size), 0)
    ImageDraw.Draw(extent).ellipse((0, 0, size - 1, size - 1), fill=255)
    extent = np.asarray(extent) > 128

    # Wide enough that the arc takes a real bite out of the shoulders, which is
    # where it showed on the two round sources rather than at the centre.
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle(
        (int(size * 0.1), int(size * 0.3), int(size * 0.9), size - 1),
        fill=(120, 40, 60, 255),
    )
    clipped = np.asarray(image).copy()
    clipped[~extent] = 0
    return Image.fromarray(clipped, "RGBA"), extent


def test_a_subject_cut_off_by_a_curved_photo_edge_is_carried_on():
    """The arc of a round source truncates the shirt as surely as a flat edge."""
    cut_out, extent = round_torso(200)
    shoulder = int(cut_out.width * 0.15)
    before = np.asarray(cut_out)[:, :, 3]
    # the arc really does end this column early, well above the frame
    assert (before[:, shoulder] > 128).any()
    assert not (before[int(cut_out.height * 0.9), shoulder] > 128)

    extended = portraits.extend_below(cut_out, extent)

    assert extended.height > cut_out.height
    after = np.asarray(extended)[:, :, 3]
    # it now runs unbroken from the shirt down past where the circle stopped
    assert after[int(cut_out.height * 0.9), shoulder] > 128
    assert after[cut_out.height + 10, shoulder] > 128


def test_the_arc_is_filled_across_the_whole_shirt():
    """A bite out of one shoulder is exactly what the round sources showed."""
    cut_out, extent = round_torso(200)

    extended = portraits.extend_below(cut_out, extent)

    alpha = np.asarray(extended)[:, :, 3]
    row = int(cut_out.height * 0.9)
    shirt = slice(int(cut_out.width * 0.15), int(cut_out.width * 0.85))
    assert (alpha[row, shirt] > 128).all()


def test_a_round_source_whose_subject_stops_inside_the_circle_is_left_alone():
    """Being round is not itself a reason to invent shirt."""
    size = 200
    extent = Image.new("L", (size, size), 0)
    ImageDraw.Draw(extent).ellipse((0, 0, size - 1, size - 1), fill=255)
    extent = np.asarray(extent) > 128

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle(
        (int(size * 0.35), int(size * 0.3), int(size * 0.65), int(size * 0.55)),
        fill=(120, 40, 60, 255),
    )

    assert portraits.extend_below(image, extent).size == image.size


# --- what the config records -------------------------------------------------

def test_registry_sources_are_reported_rather_than_failing_when_absent():
    """images/ is a local workspace, so a recorded source is often not there."""
    registry = {
        "here": {"source": "scripts/portraits.toml"},   # a file that does exist
        "gone": {"source": "images/nothing/at/all.png"},
        "no_source": {"note": "left alone"},
    }
    found, missing = portraits.registry_sources(registry)

    assert [member for member, _ in found] == ["here"]
    assert [member for member, _ in missing] == ["gone"]


def test_every_recorded_source_has_a_member_id_that_looks_like_a_portrait():
    """Guard against a typo in portraits.toml quietly building nothing."""
    registry = portraits.load_registry()
    assert registry, "portraits.toml should not be empty"
    for member, entry in registry.items():
        assert member == member.lower()
        assert " " not in member
        if "size" in entry:
            assert entry["size"] in portraits.SIZE_LADDER
