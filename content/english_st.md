---
title: Semantic transparency measures for English compounds
summary: "Semantic transparency measures for 1,865 English compounds."
nav_order: 8
parent: software-resources
permalink: /software-resources/english_st/
source: https://sites.google.com/site/fritzgntr/software-resources/english_st
---

### Existing compounds

This dataset contains semantic transparency measures for a set of 1,865 English compound words, such as *airport* or *ladybird*. It is included as Supplemental Material to the following article:

[Günther, F., & Marelli, M. (2018). Enter sand-man: Compound processing and semantic transparency in a compositional perspective. *Journal of Experimental Psychology: Learning, Memory, and Cognition*.](https://doi.org/10.1037/xlm0000677)

[**Link to the dataset**](http://supp.apa.org/psycarticles/supplemental/xlm0000677/XLM-2018-0127_elp_data.txt)

The measures are obtained from an English distributional semantic space, where each word is represented as a high-dimensional numerical vector. Using this semantic space, **modifier relatedness (simMO)** is computed as the cosine similarity between modifier and compound, *cos(air, airport)* , and analogously **head relatedness (simHO)** as the cosine similarity between head and compound, *cos(port, airport)*.

Furthermore, a compositional model was employed to obtain compositional meaning representations for the compounds (i.e., the meaning that would be predicted given the combination of their constituents). With this compositional meaning, **modifier composition (simMC)** is computed as the cosine similarity between modifier and compositional compound, *cos(air,[air+port])*, **head composition (simHC)** as the cosine similarity between headand compositional compound, *cos(port, [air+port])*, and **compound compositionality (simOC)** as the cosine similarity between actual and compositional compound, *cos(airport, [air+port]).*

For more details, see the article ([Günther & Marelli, 2018](https://doi.org/10.1037/xlm0000677))

### Novel compounds

This dataset contains the same measures for a set of almost 2 million novel English compound words, that is words consisting of two constituents that are not observed in our source corpus (such as *cottonwatch, zeroworker,* or *thunderdad)*. Please cite the following article when using this dataset (which includes additional details on the dataset), where it was the candidate set described at the beginning of the *Material* section of Experiment 1:

[Günther, F., & Marelli, M. (2020). Trying to make it work: Compositional effects in the processing of compound “nonwords”. *Quarterly Journal of Experimental Psychology*, *73*(7), 1082-1091.](https://doi.org/10.1177/1747021820902019)

[**Link to the dataset**](https://www.lingexp.uni-tuebingen.de/z2/compound_measures/novel_compounds_metrics.txt)

Note that measures relying on an observed compound representation (head and modifier relatedness, as well as compound compositionality) cannot be computed for novel compound (since they are not observed in a corpus). Therefore, the dataset only contains **modifier composition** (**simMC**), **head composition** (**simHC**), as well as **constituent similarity** (**simMH**, the similarity between the modifier and the head).

The article ([Günther & Marelli, 2020](https://doi.org/10.1177/1747021820902019)) contains an analysis of processing times for a subset of the dataset presented here.
