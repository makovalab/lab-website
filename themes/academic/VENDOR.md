# Vendored theme

This directory is a **vendored copy** of the Academic theme, not a git submodule.

| | |
|---|---|
| Upstream | https://github.com/gcushen/hugo-academic.git |
| Commit | `5c0c7f5deffe98b1c1a7b48e632815409133a7dc` (2018-12-12) |
| Version | 3.2.0-dev (`data/academic.toml`) |
| License | MIT (see `LICENSE.md`) |
| Vendored | 2026-07-30 |

## Why it is vendored

Upstream has been unmaintained at this commit since 2018 and has since been
renamed/rewritten as Wowchemy and then Hugo Blox, with no upgrade path that
preserves this site's layouts or front matter. Templates here have been
**patched locally** for Hugo 0.164, so the tree no longer matches upstream.

Tracking it as ordinary files (rather than a submodule pinned to a repo that may
disappear) keeps the site buildable without a network fetch, and lets the
required patches live in this repo's history.

## Local changes

Everything after the initial vendoring commit is ours. To see them:

```
git log --oneline -- themes/academic/
git diff <initial-vendor-commit> HEAD -- themes/academic/
```

The patches replace Hugo template APIs removed between 0.50 and 0.164
(`.Hugo`, `.Site.RSSLink`, `.Site.IsServer`, `.Site.GoogleAnalytics`,
`.Site.DisqusShortname`, `.Site.Author`, `Page.URL`, `Page.Dir`,
`Page.UniqueID`, `.Site.Data`, `.Site.LanguageCode`), restore Hugo 0.50's home
page `.Data.Pages` semantics in `layouts/partials/widget_page.html`, and pin the
Hugo 0.50 `youtube` shortcode markup so embedded videos do not change.

## Stripped from upstream

`.git/`, `.github/`, `exampleSite/`, `images/`, `academic.png`, `demo.sh`,
`.editorconfig`, `.gitignore`. `exampleSite/` in particular contains buildable
demo content that would otherwise be published.
