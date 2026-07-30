[www.bx.psu.edu/makova_lab](https://www.bx.psu.edu/makova_lab/) ![Build and Deploy](https://github.com/makovalab/lab-website/actions/workflows/build-and-deploy.yml/badge.svg?branch=master)
===

### Hugo

We use [Hugo](https://gohugo.io/) to build our site.  Installation instructions can be found [here](https://gohugo.io/getting-started/installing/).

The site is built with **Hugo 0.164.0**, pinned in
[`.github/workflows/build-and-deploy.yml`](.github/workflows/build-and-deploy.yml).
Use that same version locally — the theme is patched for it and will not build on
older releases.

The theme lives in `themes/academic/` as ordinary tracked files rather than a
submodule; see [`themes/academic/VENDOR.md`](themes/academic/VENDOR.md).

## Usage

You can clone the repo using:

```
$ git clone https://github.com/makovalab/lab-website.git
```

You can build the site using:

```
$ cd lab-website
$ hugo
```

You can test out the site using:

```
$ hugo server
```
