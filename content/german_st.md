---
title: Semantic Transparency Measures for German Compounds
summary: "Semantic transparency measures for German compounds, validated in multiple tasks."
nav_order: 9
parent: software-resources
permalink: /software-resources/german_st/
source: https://sites.google.com/site/fritzgntr/software-resources/german_st
---

This dataset contains semantic transparency measures for a set of 1,810 German compound words, such as *Flughafen* (*airport)* or *Zebrastreifen (crosswalk)*, and is validated against human behavioral data in multiple empirical studies, as reported in the following article:

[Günther, F., Marelli, M., & Bölte, J. (2020). Semantic transparency effects in German compounds: A large dataset and multiple-task investigation*. Behavior Research Methods, 52,* 1208-1224.](https://doi.org/10.3758/s13428-019-01311-4)

We further provide the same semantic transparency measures for a dataset of 40,475 additional German compounds, as well as for 2,061 novel German compounds.

[**Link to the dataset**](https://doi.org/10.6084/m9.figshare.8295101)

The measures are obtained from a German distributional semantic space, where each word is represented as a high-dimensional numerical vector. Using this semantic space, **modifier relatedness** is computed as the cosine similarity between modifier and compound, *cos(Flug, Flughafen)* , and analogously **head relatedness** as the cosine similarity between head and compound, *cos(Hafen, Flughafen)*. Furthermore, **constituent similarity** is defined as the cosine similarity between the two constituents, *cos(Flug, Hafen)*.

Furthermore, a compositional model was employed to obtain compositional meaning representations for the compounds (i.e., the meaning that would be predicted given the combination of their constituents). With this compositional meaning, **modifier composition** is computed as the cosine similarity between modifier and compositional compound, *cos(Flug, [Flug+Hafen])*, **head composition** as the cosine similarity between headand compositional compound, *cos(Hafen, [Flug+Hafen])*, and **compound compositionality** as the cosine similarity between actual and compositional compound, *cos(Flughafen, [Flug+Hafen]).*

For more details, see the article ([Günther, Marelli, & Bölte, 2020](https://doi.org/10.3758/s13428-019-01311-4))
