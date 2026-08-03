---
title: Members
# RSS only. The old site published a feed here listing every member, and
# dropping it would break anything subscribed. The HTML page at /member/ is not
# this section's -- content/people/_index.md claims that URL as an alias, and
# emitting no HTML here leaves that alone.
outputs:
  - RSS
# The URL here is a redirect stub to /people/, so keep it out of the sitemap --
# the feed is the only thing this section exists to serve.
sitemap:
  disable: true
# Which author groups this feed covers.
groups:
  - Members
  - Former Members
---
