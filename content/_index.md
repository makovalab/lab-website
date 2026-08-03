---
title: ''
date: 2018-12-13
type: landing

# Block `id`s reproduce the anchors the old widget pages generated
# (content/home/<name>.md became #<name>), so the existing main menu keeps working.
sections:
  - block: hero
    id: hero_carousel
    content:
      title: The Makova Lab at Penn State
      text: Genomics, evolution, and human genetics.
    design:
      background:
        # The white here is not decoration: `contain` letterboxes the diagram
        # whenever the window is not its own 2.76 shape, and the brightness
        # filter below applies to this colour and to the image alike, so both
        # land on the same grey and the letterboxing does not show as a band.
        color: '#ffffff'
        image:
          # Labelled version is Makova_BDNA_HERO_0.jpg, kept as the source. Its
          # "non-B DNA" and "B-DNA" were set to the right of the artwork, so any
          # crop cut through them.
          filename: Makova_BDNA_HERO_no_labels.png
          # `cover` filled the box by cropping, which took the bottom off the
          # strands at desktop widths and both ends of them below about 1900px.
          # The diagram is the point of the image, so fit it whole instead.
          size: contain
          # Parallax means background-attachment: fixed, which sizes the image
          # against the viewport rather than this 688px-tall box -- `contain`
          # would then fit it to the window and shrink it out of the hero.
          parallax: false
          # No brightness filter. It was set to 0.6, which is the right move for
          # a photographic hero with white text over it -- but this hero's text
          # is dark and the diagram is drawn on white, so darkening it worked
          # against both, greying the artwork and flattening the title's
          # contrast against it.

  - block: collection
    id: projects
    content:
      title: Projects
      filters:
        folders:
          - project
    design:
      view: article-grid
      columns: 2

  - block: collection
    id: news
    content:
      title: News
      count: 5
      filters:
        folders:
          - news
    design:
      # News, Press Releases and Publications are three text lists in a row with
      # no cards to tell them apart -- the one stretch of this page where a
      # reader cannot see where one section ends. All three carry the same tint,
      # so they read as a single band against the white sections either side
      # rather than as stripes. Nothing else is tinted; the other sections are
      # card grids and separate themselves.
      background:
        color:
          light: '#f8fafc'
          dark: '#172032'
      view: date-title-summary

  - block: collection
    id: press_releases
    content:
      title: Press Releases
      count: 5
      filters:
        folders:
          - press_release
    design:
      # News, Press Releases and Publications are three text lists in a row with
      # no cards to tell them apart -- the one stretch of this page where a
      # reader cannot see where one section ends. All three carry the same tint,
      # so they read as a single band against the white sections either side
      # rather than as stripes. Nothing else is tinted; the other sections are
      # card grids and separate themselves.
      background:
        color:
          light: '#f8fafc'
          dark: '#172032'
      view: date-title-summary

  - block: collection
    id: publications
    content:
      title: Publications
      count: 10
      filters:
        folders:
          - publication
    design:
      # News, Press Releases and Publications are three text lists in a row with
      # no cards to tell them apart -- the one stretch of this page where a
      # reader cannot see where one section ends. All three carry the same tint,
      # so they read as a single band against the white sections either side
      # rather than as stripes. Nothing else is tinted; the other sections are
      # card grids and separate themselves.
      background:
        color:
          light: '#f8fafc'
          dark: '#172032'
      view: citation

  - block: collection
    id: videos
    content:
      title: Videos
      filters:
        folders:
          - video
    design:
      view: card

  # Current people only, matching the pre-migration homepage widgets, which
  # skipped anyone flagged `is_former_member` / `is_former_collaborator`.
  # Alumni live on /people/, linked from the CTA below.
  - block: team-showcase
    id: members
    content:
      title: Members
      user_groups:
        - Members
      sort_by: weight
      sort_ascending: true
      cta:
        text: All members
        url: /people/
    design:
      show_role: true
      show_organizations: true
      show_interests: false
      max_columns: 4

  - block: team-showcase
    id: collaborators
    content:
      title: Collaborators
      user_groups:
        - Collaborators
      sort_by: weight
      sort_ascending: true
      # No call to action here on purpose. The Members block has one because
      # this page shows 9 of 65 and the rest are worth a click. Every
      # collaborator is already on this page -- nobody is flagged
      # `Former Collaborators` -- so the button led to the same twenty people it
      # was sitting under. Restore it, pointing at /people/#collaborators, once
      # some collaborators are retired and the two lists differ.
    design:
      show_role: true
      show_organizations: true
      show_interests: false
      max_columns: 4

  - block: contact-info
    id: contact
    content:
      title: Contact
      email: kdm16@bx.psu.edu
      phone: '+1-814-863-1619'
      # The address the migration carried over kept the old theme's shape --
      # street / city / region / postcode / country. This block reads
      # `address.lines` or a plain string and ignores anything else, so the
      # address was in the config but nothing rendered it and the lab's postal
      # address had quietly dropped off the site.
      address:
        lines:
          - 310 Wartik Lab
          - University Park, Pennsylvania 16802
          - United States
      # Built from the latitude and longitude the old config carried
      # (40.799720, -77.862522), which nothing here reads directly. The old site
      # showed an embedded map; this block also takes `map_embed` for an iframe
      # if that is wanted back, at the cost of loading a third-party map on the
      # front page.
      map_url: https://www.google.com/maps/search/?api=1&query=40.799720,-77.862522
---
