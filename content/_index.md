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
        image:
          filename: Makova_BDNA_HERO_0.jpg
          filters:
            brightness: 0.6

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
      cta:
        text: All collaborators
        url: /people/
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
      address:
        street: 310 Wartik Lab
        city: University Park
        region: Pennsylvania
        postcode: '16802'
        country: United States
        country_code: US
      coordinates:
        latitude: '40.799720'
        longitude: '-77.862522'
---
