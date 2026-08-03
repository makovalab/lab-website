# Making member portraits

Member photos on this site are round, sit on the same flat background, and are
200, 400 or 600 pixels square depending on what their photo can support.
`make-portraits` does that conversion for you, so you can start from an ordinary
photo straight off a phone or camera.

## Using it

1. **Copy the photo into `photos/inbox/`**, named after the member.

   The name matters: it becomes the portrait's filename. Use the same id as the
   member's page in `content/member/`. If the page is
   `content/member/linnea_smeds.md`, name the photo `linnea_smeds.jpg`.

   The extension can be `.jpg`, `.png`, `.heic`-converted, whatever — just keep
   the name before the dot right.

2. **Run the script**, from the top of the repository:

   ```
   ./scripts/make-portraits
   ```

   The first run takes a few minutes: it builds its own private Python
   environment and downloads the background-removal model. It needs an internet
   connection that first time. After that it starts immediately.

3. **Look at the result** in `static/img/member/`, then commit it:

   ```
   git add static/img/member && git commit -m "update member portraits"
   ```

You can leave several photos in the inbox at once; they all get processed.

## What it does to the photo

- Rotates it if the camera stored it sideways.
- Cuts the person out and puts them on a flat light-grey background, so all the
  portraits match.
- Finds the face and takes a square crop around it.
- Rounds off the corners.

## How big the portrait comes out

Every portrait draws the head at the same fraction of the frame, so how large it
can be made is decided by how much of the original the head actually fills. The
script measures that and picks the largest of 200, 400 or 600 that the photo can
fill without being enlarged — roughly 124, 248 and 372 pixels from crown to chin.
Enlarging past that invents detail rather than showing more.

You do not have to choose: a phone photo of someone's face usually lands at 600,
a small crop salvaged from an old page at 200. The site scales whatever it gets
down to the size the page needs, so one file per person is enough.

To override it — say a photo is nominally large but soft — record a `size` for
that person in `portraits.toml`, or pass `--size` to force a whole run.

## Adding a new member

The portrait is only half of it — the member also needs a page. Copy an existing
one in `content/member/` as a starting point and make sure its `portrait =` line
matches the file you just created:

```toml
portrait = "linnea_smeds.png"
```

## When something goes wrong

The script tells you which photos it could not handle and why, and processes the
rest regardless. The usual problems:

**"no face detected"** — the face is too small, too far to the side, or at too
much of an angle. Use a photo where the person is looking roughly at the camera
and their face fills a decent part of the frame. If you would rather crop it
yourself, cut it to a square centred on the face and run:

```
./scripts/make-portraits --no-detect
```

**"… already exists"** — you are replacing a portrait that is already in the
repo. That is fine, it just wants you to confirm:

```
./scripts/make-portraits --force
```

**It picked the wrong person** in a group photo. It chooses the largest face.
Crop the photo down to the person you want first.

**"could not create a Python environment"** — Python's virtual environment
support is missing. On Ubuntu or Debian, run the `apt install` command the error
message names. On macOS, `brew install python`.

## Options

Run `./scripts/make-portraits --help` for the full list. The useful ones:

| Option | Effect |
| --- | --- |
| `--force` | Replace portraits that already exist |
| `--no-detect` | Skip face detection; centre-crop instead |
| `--keep-background` | Leave the photo's own background alone |
| `--background '#ffffff'` | Use a different flat colour |
| `--size 400` | Force an edge length instead of measuring one |
| `--from-registry` | Rebuild every portrait recorded in `portraits.toml` |
| `--out DIR` | Write somewhere other than `static/img/member/` |

You can also name photos directly instead of using the inbox:

```
./scripts/make-portraits ~/Desktop/IMG_4821.jpg
```

## Rebuilding a portrait later

`portraits.toml` records which original photo each portrait was made from, along
with any setting that person needed. That matters because the filename rarely
matches the member: several people had an older photo, an illustration, or an
entirely different person sharing a filename, and the right original was only
established by comparing faces (`verify_portrait_sources.py`). To rebuild every
portrait that has a recorded source:

```
./scripts/make-portraits --from-registry
```

The originals live in `photos/originals/`, one per member, named after them.
They are committed on purpose: a portrait you cannot remake is a portrait you
can only lose, and the workspace these were recovered from is not in the
repository and has already been partly lost once.

**Not everyone has one.** Fourteen members do. For the other twenty-four the
committed PNG in `static/img/member/` is the only copy in existence — there is
no original to go back to. Treat those as originals in their own right: do not
run them through the script hoping to improve them, because a bad matte or a
wrong source overwrites the only thing we have. `--from-registry` only touches
members with a recorded source, which is exactly why it is the safe way to
rebuild.

## For maintainers

`portraits.py` holds the logic; `make-portraits` is a wrapper that manages the
Python environment. The environment lives in `scripts/.venv` and is ignored by
git — delete it to force a clean rebuild.

`./scripts/make-portraits --test` runs the checks in `test_portraits.py`. They
cover the framing maths — the size ladder, and that the framing and the circle's
soft edge are the same shape at 200, 400 and 600 — and take about a second,
since they use synthetic images rather than the background-removal model. Run
them after touching the constants at the top of `portraits.py`: a measurement
accidentally written in pixels rather than as a fraction of `SIZE` still looks
right on its own and only shows up as portraits that stop matching each other.

Dependency versions are pinned in `requirements.txt` so that regenerating a
portrait years from now gives the same result. The wrapper reinstalls whenever
that file is newer than the last install.

The look of the portraits is set by the constants at the top of `portraits.py`
(`SIZE`, `BACKGROUND`, `CROP_SCALE`). Changing them affects new portraits only;
existing ones would need regenerating from their source photos.
