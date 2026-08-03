# Vendored model

`face_detection_yunet_2023mar.onnx` — YuNet face detector from
[OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet),
MIT licensed, 227 KB.

Committed rather than downloaded on first run so the tool works offline and
cannot break because an upstream URL moved.

It is used in preference to the Haar cascades because it returns the eye centres
directly and, being a small neural network rather than a texture matcher, it
still finds them behind glasses and sunglasses. On this lab's photos the Haar
eye cascades failed on 7 of 15; YuNet found eyes on all of them.

## The model that is deliberately *not* here

Identifying which archived photo each published portrait was cut from took a
second model as well: SFace, from the same OpenCV Zoo under
`models/face_recognition_sface`, 37 MB:

```
face_recognition_sface_2021dec.onnx
sha256  0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79
```

It is not committed, because 37 MB is a lot of repository for a job that is
finished and whose answers are now written down in `portraits.toml`. Nothing in
the repo loads it. If you ever need it again, fetch it from the Zoo and put it
beside this file.

Why it was needed, since `verify_portrait_sources.py` already matches faces:
that script compares faces by *normalised cross-correlation of the pixels*,
which answers "is this the same photograph?" and nothing else. That is the right
question most of the time and it is cheap. It goes vague exactly where the
archive was messiest — when the only surviving copy of an original had been
resized and re-encoded on its way through some old page, and when one photo
existed in half a dozen near-duplicates and they all scored alike. SFace scores
*identity* instead, comparing face embeddings rather than pixels, so it still
recognises a person across a resize, and it separates a genuinely different
person who happens to share a filename from a mangled copy of the right one. The
source recorded for each person in `portraits.toml` came out of that pass.

Two things to know before repeating it:

- **Widen the candidate pool before you trust a low score.** The first pass over
  the archive gave Arpita a top match of 0.31 — a different person entirely.
  Nothing was wrong with the matching; her original simply was not in the pool
  yet. Adding images recovered from the site's own git history turned that into
  a 0.96 match on the real photo. A weak best-match usually means the source is
  missing, not that the source is bad.
- **Rank by score, never by face size.** It is tempting to sort the survivors by
  how many pixels wide the face is, since that is what limits portrait quality.
  A tight crop of the head wins that contest by definition while being the worse
  source — it is the same photo with the shirt cut off. That mistake is what put
  Kaivan and Karol on cropped originals for a while.
