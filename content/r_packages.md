---
title: R packages
summary: "LSAfun — R functions for working with semantic spaces (on CRAN)."
nav_order: 1
parent: software-resources
kind: R package
permalink: /software-resources/r_packages/
source: https://sites.google.com/site/fritzgntr/software-resources/r_packages
---

### R Packages

To download R, click [here](https://www.r-project.org/)

My R package *LSAfun* is available at [CRAN](https://cran.r-project.org/web/packages/LSAfun/index.html)

This package contains a collection of useful standard functions for working with semantic spaces (for example *Latent Semantic Analysis*, *LSA*). The R manual is available [here](https://cran.r-project.org/web/packages/LSAfun/LSAfun.pdf). A more detailed manual with instructions as well as some theoretical background is available in the following article:

Günther, F., Dudschig, C., & Kaup, B. (2015). LSAfun – An R package for computations based on Latent Semantic Analysis. *Behavior Research Methods, 47,* 930-944. [Link](https://link.springer.com/article/10.3758/s13428-014-0529-0) [Download](https://drive.google.com/open?id=1aplYVVJ1SLtO5Z04EY2ZJG16l-eAQLSO)

### Note

The *LSAfun* package is *not* designed for creating semantic spaces. To create semantic spaces (from small corpora) in R, use the package [lsa](https://cran.r-project.org/web/packages/lsa/index.html).

If you want to build semantic spaces from larger text corpora, it makes sense to use specialized software packages, such as [S-Space](https://github.com/fozziethebeat/S-Space), [DISSECT](http://clic.cimec.unitn.it/composes/toolkit/), [SemanticVectors](https://github.com/semanticvectors/semanticvectors/wiki), [gensim](https://radimrehurek.com/gensim/)

If you are interested in using [word2vec](https://code.google.com/p/word2vec/) word embedings, here are some very fine options to create those in R: [rword2vec](https://github.com/mukul13/rword2vec) and [wordVectors](https://github.com/bmschmidt/wordVectors)

These packages create word2vec embeddings in R using only one line of code, and run decently fast also on local machines!

Alternatively, there are many pre-built semantic spaces publicly available! Check out the [Semantic Spaces](/software-resources/semantic_spaces/) repository provided on this page.
