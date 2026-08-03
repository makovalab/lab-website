---
title: Authors
# `author` is a taxonomy, so Hugo builds a term page for every distinct author
# string in the publications -- around 1,250, nearly all of them co-authors from
# other institutions who would each get a page here with nothing on it.
#
# So terms are off by default and the lab's own people opt back in, each with a
# `build` block in their own _index.md. Anyone without one still groups papers
# together internally; they simply have no page of their own, which is why the
# citation template links a name only when data/author_links.yaml knows it.
# The cascade below reaches this page as well, so it says plainly that the
# listing itself stays.
build:
  render: always
  list: always
cascade:
  - build:
      render: never
      list: never
---
