# Making member portraits

Member photos on this site are round, 200×200 pixels, and sit on the same flat
background. `make-portraits` does that conversion for you, so you can start from
an ordinary photo straight off a phone or camera.

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
- Scales that to 200×200 and rounds off the corners.

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
| `--out DIR` | Write somewhere other than `static/img/member/` |

You can also name photos directly instead of using the inbox:

```
./scripts/make-portraits ~/Desktop/IMG_4821.jpg
```

## For maintainers

`portraits.py` holds the logic; `make-portraits` is a wrapper that manages the
Python environment. The environment lives in `scripts/.venv` and is ignored by
git — delete it to force a clean rebuild.

Dependency versions are pinned in `requirements.txt` so that regenerating a
portrait years from now gives the same result. The wrapper reinstalls whenever
that file is newer than the last install.

The look of the portraits is set by the constants at the top of `portraits.py`
(`SIZE`, `BACKGROUND`, `CROP_SCALE`). Changing them affects new portraits only;
existing ones would need regenerating from their source photos.
