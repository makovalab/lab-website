[www.bx.psu.edu/makova_lab](https://www.bx.psu.edu/makova_lab/) ![Build and Deploy](https://github.com/makovalab/lab-website/actions/workflows/build-and-deploy.yml/badge.svg?branch=master)
===

### Hugo

We use [Hugo](https://gohugo.io/) to build our site.  Installation instructions can be found [here](https://gohugo.io/getting-started/installing/).

## Usage

You can clone the repo using:

```
$ git clone --recursive https://github.com/makovalab/lab-website.git
```
or

```
$ git clone https://github.com/makovalab/lab-website.git
$ cd lab-website
$ git submodule update --init --recursive
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
