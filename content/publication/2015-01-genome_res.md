+++
title = "Accurate typing of short tandem repeats from genome-wide sequencing data and its applications"
date = 2015-01-01T00:00:00
draft = false

# Authors. Comma separated list, e.g. `["Bob Smith", "David Jones"]`.
authors = ["A Fungtammasan", "G Ananda", "SE Hile", "MS-W Su", "C Sun", "RS Harris", "P Medvedev", "KA Eckert", "KD Makova"]

# Publication type.
# Legend:
# 0 = Uncategorized
# 1 = Conference paper
# 2 = Journal article
# 3 = Manuscript
# 4 = Report
# 5 = Book
# 6 = Book section
publication_types = ["2"]

# Publication name and optional abbreviated version.
publication = "_Genome Research_"
publication_short = "_GENOME RES_"

# Abstract and optional shortened version.
abstract = "Short tandem repeats (STRs) are implicated in dozens of human genetic diseases and contribute significantly to genome variation and instability. Yet profiling STRs from short-read sequencing data is challenging because of their high sequencing error rates. Here, we developed STR-FM, short tandem repeat profiling using flank-based mapping, a computational pipeline that can detect the full spectrum of STR alleles from short-read data, can adapt to emerging read-mapping algorithms, and can be applied to heterogeneous genetic samples (e.g., tumors, viruses, and genomes of organelles). We used STR-FM to study STR error rates and patterns in publicly available human and in-house generated ultradeep plasmid sequencing data sets. We discovered that STRs sequenced with a PCR-free protocol have up to ninefold fewer errors than those sequenced with a PCR-containing protocol. We constructed an error correction model for genotyping STRs that can distinguish heterozygous alleles containing STRs with consecutive repeat numbers. Applying our model and pipeline to Illumina sequencing data with 100-bp reads, we could confidently genotype several disease-related long trinucleotide STRs. Utilizing this pipeline, for the first time we determined the genome-wide STR germline mutation rate from a deeply sequenced human pedigree. Additionally, we built a tool that recommends minimal sequencing depth for accurate STR genotyping, depending on repeat length and sequencing read length. The required read depth increases with STR length and is lower for a PCR-free protocol. This suite of tools addresses the pressing challenges surrounding STR genotyping, and thus is of wide interest to researchers investigating disease-related STRs and STR evolution."
abstract_short = ""

# Is this a selected publication? (true/false)
selected = false

# Projects (optional).
#   Associate this publication with one or more of your projects.
#   Simply enter your project's folder or file name without extension.
#   E.g. `projects = ["deep-learning"]` references 
#   `content/project/deep-learning/index.md`.
#   Otherwise, set `projects = []`.
projects = ["microsatellite_variation_and_evolution"]


# Slides (optional).
#   Associate this page with Markdown slides.
#   Simply enter your slide deck's filename without extension.
#   E.g. `slides = "example-slides"` references 
#   `content/slides/example-slides.md`.
#   Otherwise, set `slides = ""`.
slides = ""

# Tags (optional).
#   Set `tags = []` for no tags, or use the form `tags = ["A Tag", "Another Tag"]` for one or more tags.
tags = []

# Links (optional).
url_pdf = ""
url_preprint = ""
url_code = ""
url_dataset = ""
url_project = ""
url_slides = ""
url_video = ""
url_poster = ""
url_source = ""

# Custom links (optional).
#   Uncomment line below to enable. For multiple links, use the form `[{...}, {...}, {...}]`.
# url_custom = [{name = "Custom Link", url = "http://example.org"}]


# Digital Object Identifier (DOI)
doi = "10.1101/gr.185892.114"


# Featured image
# To use, add an image named `featured.jpg/png` to your page's folder. 
[image]
  # Caption (optional)
  caption = ""

  # Focal point (optional)
  # Options: Smart, Center, TopLeft, Top, TopRight, Left, Right, BottomLeft, Bottom, BottomRight
  focal_point = ""
+++