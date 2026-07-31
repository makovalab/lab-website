---
title: 'Family reunion via error correction: an efficient analysis of duplex sequencing data'
date: 2020-03-04 00:00:00
authors:
- N Stoler
- B Arbeithuber
- G Povysil
- M Heinzl
- R Salazar
- KD Makova
- I Tiemann-Boege
- A Nekrutenko
publication_types:
- article-journal
publication:
  name: BMC Bioinformatics
  short_name: BMC BIOINFORMATICS
abstract: '**Background**


  Duplex sequencing is the most accurate approach for identification of sequence variants present at very low frequencies. Its power comes from pooling together multiple descendants of both strands of original DNA molecules, which allows distinguishing true nucleotide substitutions from PCR amplification and sequencing artifacts. This strategy comes at a cost—sequencing the same molecule multiple times increases dynamic range but significantly diminishes coverage, making whole genome duplex sequencing prohibitively expensive. Furthermore, every duplex experiment produces a substantial proportion of singleton reads that cannot be used in the analysis and are thrown away.


  **Results**


  In this paper we demonstrate that a significant fraction of these reads contains PCR or sequencing errors within duplex tags. Correction of such errors allows “reuniting” these reads with their respective families increasing the output of the method and making it more cost effective.


  **Conclusions**


  We combine an error correction strategy with a number of algorithmic improvements in a new version of the duplex analysis software, Du Novo 2.0. It is written in Python, C, AWK, and Bash. It is open source and readily available through Galaxy, Bioconda, and Github: [https://github.com/galaxyproject/dunovo](https://github.com/galaxyproject/dunovo).'
projects:
- mitochondrial_mutation_dynamics
- microsatellite_variation_and_evolution
links:
- type: code
  url: https://github.com/galaxyproject/dunovo
hugoblox:
  ids:
    doi: 10.1186/s12859-020-3419-8
image:
  caption: ''
  focal_point: ''
---

