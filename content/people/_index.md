---
title: People
type: landing

# The pre-migration site published standalone section listings at /member/ and
# /collaborator/. Those sections no longer exist as content (people now live in
# data/authors/), so this page inherits their URLs, including the paginated
# variants the old templates emitted.
aliases:
  - /member/
  - /collaborator/
  - /collaborator/page/1/
  - /collaborator/page/2/

sections:
  - block: team-showcase
    id: members
    content:
      title: Members
      user_groups:
        - Members
        - Former Members
      sort_by: weight
      sort_ascending: true
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
        - Former Collaborators
      sort_by: weight
      sort_ascending: true
    design:
      show_role: true
      show_organizations: true
      show_interests: false
      max_columns: 4
---
