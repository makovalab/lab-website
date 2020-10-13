+++
title = "Evolution of the Y chromosome in great apes deciphered"
subtitle = "Researchers reconstruct the ancestral great ape Y and show its rapid evolution in bonobo and chimpanzee"
date = 2020-10-06T00:00:00
draft = false

# Authors. Comma separated list, e.g. `["Bob Smith", "David Jones"]`.
authors = ['Sam Sholtis']

# Tags and categories
# For example, use `tags = []` for no tags, or the form `tags = ["A Tag", "Another Tag"]` for one or more tags.
tags = []
categories = []

# Projects (optional).
#   Associate this post with one or more of your projects.
#   Simply enter your project's folder or file name without extension.
#   E.g. `projects = ["deep-learning"]` references 
#   `content/project/deep-learning/index.md`.
#   Otherwise, set `projects = []`.
projects = ["sex_chromosome_evolution"]

# Featured image
# To use, add an image named `featured.jpg/png` to your page's folder. 
[image]
  # Caption (optional)
  caption = ""

  # Focal point (optional)
  # Options: Smart, Center, TopLeft, Top, TopRight, Left, Right, BottomLeft, Bottom, BottomRight
  focal_point = ""


#[header]
#  image = "Makova7-2020_Figure_SM.jpg"

+++

{{< figure
      class="image-center"
      src="makova_apes.png"
      caption="Researchers have reconstructed the ancestral sequence of the great ape Y chromosome by comparing three existing (gorilla, human, and chimpanzee) and two newly generated (orangutan and bonobo) Y chromosome assemblies. The new research shows that many gene families and multi-copy sequences were already present in the great ape Y common ancestor and that the chimpanzee and bonobo lineages experienced accelerated gene death and nucleotide substitution rates after their divergence from the human lineage. **IMAGE: DANI ZEMBA AND MONIKA CECHOVA, PENN STATE**"
>}}

UNIVERSITY PARK, Pa. — New analysis of the DNA sequence of the male-specific Y chromosomes from all living species of the great ape family helps to clarify our understanding of how this enigmatic chromosome evolved. A clearer picture of the evolution of the Y chromosome is important for studying male fertility in humans as well as our understanding of reproduction patterns and the ability to track male lineages in the great apes, which can help with conservation efforts for these endangered species.

A team of biologists and computer scientists at Penn State sequenced and assembled the Y chromosome from orangutan and bonobo and compared those sequences to the existing human, chimpanzee, and gorilla Y sequences. From the comparison, the team were able to clarify patterns of evolution that seem to fit with behavioral differences between the species and reconstruct a model of what the Y chromosome might have looked like in the ancestor of all great apes.

A [paper describing the research]({{< ref "/publication/2020-10-p_natl_acad_sci_usa.md" >}}) appears Oct. 5 in the journal Proceedings of the National Academy of Sciences.

"The Y chromosome is important for male fertility and contains the genes critical for sperm production, but it is often neglected in genomic studies because it is so difficult to sequence and assemble," said [Monika Cechova]({{< ref "/member/monika_cechova.md" >}}), a graduate student at Penn State at the time of the research and co-first author of the paper. "The Y chromosome contains a lot of repetitive sequences, which are challenging for DNA sequencing, assembling sequences, and aligning sequences for comparison. There aren't out-of-the-box software packages to deal with the Y chromosome, so we had to overcome these hurdles and optimize our experimental and computational protocols, which allowed us to address interesting biological questions."

The Y chromosome is unusual. It contains relatively few genes, many of which are involved in male sex determination and sperm production; large sections of repetitive DNA, short sequences repeated over and over again; and large DNA palindromes, inverted repeats that can be many thousands of letters long and read the same forwards and backwards.

Previous work by the team comparing human, chimpanzee, and gorilla sequences had revealed some unexpected patterns. Humans are more closely related to chimpanzees, but for some characteristics, the human Y was more similar to the gorilla Y.

"If you just compare the sequence identity — comparing the As,Ts, Cs, and Gs of the chromosomes — humans are more similar to chimpanzees, as you would expect," said [Kateryna Makova]({{< ref "/member/kateryna_makova.md" >}}), Pentz Professor of Biology at Penn State and one of the leaders of the research team. "But if you look at which genes are present, the types of repetitive sequences, and the shared palindromes, humans look more similar to gorillas. We needed the Y chromosome of more great ape species to tease out the details of what was going on."

The team, therefore, sequenced the Y chromosome of a bonobo, a close relative of the chimpanzee, and an orangutan, a more distantly related great ape. With these new sequences, the researchers could see that the bonobo and chimpanzee shared the unusual pattern of accelerated rates of DNA sequence change and gene loss, suggesting that this pattern emerged prior to the evolutionary split between the two species. The orangutan Y chromosome, on the other hand, which serves as an outgroup to ground the comparisons, looked about like what you expect based on its known relationship to the other great apes.

"Our hypothesis is that the accelerated change that we see in chimpanzees and bonobos could be related to their mating habits," said [Rahulsimham Vegesna]({{< ref "/member/rahulsimham_vegesna.md" >}}), a graduate student at Penn State and co-first author of the paper. "In chimpanzees and bonobos, one female mates with multiple males during a single cycle. This leads to what we call 'sperm competition,' the sperm from several males trying to fertilize a single egg. We think that this situation could provide the evolutionary pressure to accelerate change on the chimpanzee and bonobo Y chromosome, compared to other apes with different mating patterns, but this hypothesis, while consistent with our findings, needs to be evaluated in subsequent studies."

In addition to teasing out some of the details of how the Y chromosome evolved in individual species, the team used the set of great ape sequences to reconstruct what the Y chromosome might have looked like in the ancestor of modern great apes.

"Having the ancestral great ape Y chromosome helps us to understand how the chromosome evolved," said [Vegesna]({{< ref "/member/rahulsimham_vegesna.md" >}}). "For example, we can see that many of the repetitive regions and palindromes on the Y were already present on the ancestral chromosome. This, in turn, argues for the importance of these features for the Y chromosome in all great apes and allows us to explore how they evolved in each of the separate species."

The Y chromosome is also unusual because, unlike most chromosomes it doesn't have a matching partner. We each get two copies of chromosomes 1 through 22, and then some of us (females) get two X chromosomes and some of us (males) get one X and one Y. Partner chromosomes can exchange sections in a process called 'recombination,' which is important to preserve the chromosomes evolutionarily. Because the Y doesn't have a partner, it had been hypothesized that the long palindromic sequences on the Y might be able to recombine with themselves and thus still be able to preserve their genes, but the mechanism was not known.

"We used the data from a technique called Hi-C, which captures the three-dimensional organization of the chromosome, to try to see how this 'self-recombination' is facilitated," said [Cechova]({{< ref "/member/monika_cechova.md" >}}). "What we found was that regions of the chromosome that recombine with each other are kept in close proximity to one another spatially by the structure of the chromosome."

"Working on the Y chromosome presents a lot of challenges," said [Paul Medvedev]({{< ref "/collaborator/paul_medvedev.md" >}}), associate professor of computer science and engineering and of biochemistry and molecular biology at Penn State and the other leader of the research team. "We had to develop specialized methods and computational analyses to account for the highly repetitive nature of the sequence of the Y. This project is truly cross-disciplinary and could not have happened without the combination of computational and biological scientists that we have on our team."

In addition to [Cechova]({{< ref "/member/monika_cechova.md" >}}), [Makova]({{< ref "/member/kateryna_makova.md" >}}), [Vegesna]({{< ref "/member/rahulsimham_vegesna.md" >}}), and [Medvedev]({{< ref "/collaborator/paul_medvedev.md" >}}), the research team at Penn State included [Marta Tomaszkiewicz]({{< ref "/member/marta_tomaszkiewicz.md" >}}), [Robert S. Harris]({{< ref "/member/robert_harris.md" >}}), [Di Chen]({{< ref "/member/di_chen.md" >}}), and [Samarth Rangavittal]({{< ref "/member/samarth_rangavittal.md" >}}).  The research was supported by the U.S. National Institutes of Health, the U.S. National Science Foundation, the Clinical and Translational Sciences Institute, the Institute of Computational and Data Sciences, the Huck Institutes of the Life Sciences, and the Eberly College of Science of the Pennsylvania State University, and by the CBIOS Predoctoral Training Program awarded to Penn State by the National Institutes of Health.

**MEDIA CONTACTS**\
\
**Kateryna Makova**, <a href="mailto:kdm16@psu.edu">kdm16@psu.edu</a>\
*Work Phone: 814-863-1619*\
\
**Sam Sholtis**, <a href="mailto:sjs144@psu.edu">sjs144@psu.edu</a>\
*Work Phone: 814-865-1390*

