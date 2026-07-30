# photos/

Working area for turning ordinary photos into member portraits.

Put a photo in `inbox/`, named after the member (`linnea_smeds.jpg` for the
member whose page is `content/member/linnea_smeds.md`), then run:

```
./scripts/make-portraits
```

The finished portrait is written to `static/img/member/` and *that* is what gets
committed. See [`scripts/README.md`](../scripts/README.md) for the details.

## What is and isn't kept

The contents of `inbox/` are **not** committed — they are source material, often
large, and the site only needs the finished 200×200 portrait. Keep the originals
somewhere durable of your own (a shared drive, for instance) in case a portrait
ever needs regenerating at a different size or crop.
