---
title: Semantic Spaces
summary: "Ready-to-use semantic spaces for English, German, Italian, Spanish and French."
nav_order: 2
parent: software-resources
kind: Download
permalink: /software-resources/semantic_spaces/
source: https://sites.google.com/site/fritzgntr/software-resources/semantic_spaces
---

If you want to start working with semantic spaces without having to build one on your own,
you can use several freely available semantic spaces. Just always be sure that you have an
understanding on what kind of semantic space you are using, which algorithm was used to
create it, and which text corpus served as a basis.

Several high-performing semantic spaces, including *word2vec* word embeddings, are available
from [Marco Baroni's group](http://clic.cimec.unitn.it/composes/semantic-vectors.html). This page also includes an article evaluating these spaces.<br>
These spaces are thoroughly tested on a number of tasks.<br>
They are provided in an R-readable .txt format; once you have downloaded and unzipped them,<br>
`read.table("NAME.txt",quote="",comment="",sep="\t",row.names=1)`<br>
\- or an fread() equivalent - should do the job of importing them.

You can also use the pre-trained [GloVe spaces](https://nlp.stanford.edu/projects/glove/) by Pennington, Socher, & Manning, provided at
the Stanford NLP website, which are also avialable in a plain .txt format, or the [SNAUT](http://meshugga.ugent.be/snaut//spaces/) spaces by<br>
Mandera, Keuleers, & Brysbaert.

Another list of pre-trained vectors in a variety of languages was collected by [Ahogrammer](http://ahogrammer.com/2017/01/20/the-list-of-pretrained-word-embeddings/).<br>
A huge collection of pre-trained vectors in many different languages is available from
[Facebook Research](https://github.com/facebookresearch/fastText/blob/master/docs/crawl-vectors.md).

## Downloadable semantic spaces

All the semantic spaces provided here are available in the .rda format for R.<br>
Load them into the R workspace using:<br>
`load("NAMEOFSPACE.rda")`

If you want to use the spaces outside of R, you can export them as .txt (or another preferred format) using the following command:<br>
`write.table(NAMEOFSPACE,file="NAMEOFSPACE.txt",row.names=T,col.names=F)`

If you don't want to use R at all, you can contact me and I can provide you with the .txt files for the semantic space

You're helping me a lot by citing the following article in research using these semantic spaces:<br>
Günther, F., Dudschig, C., & Kaup, B. (2015). LSAfun – An R package for computations based
on Latent Semantic Analysis. *Behavior Research Methods, 47,* 930-944.

The currently available spaces are:

- **TASA** — English LSA Space, 300 dimensions
- **EN_100k** — English HAL Space, 300 dimensions
- **EN_100k_lsa** — English LSA Space, 300 dimensions
- **EN_100k_cbow** — English cbow space, 300 dimensions
- **baroni** — English cbow space, 400 dimensions
- **ukwac_cbow** — English cbow space, 400 dimensions
- **frwak100k** — French HAL Space, 300 dimensions
- **dewak100k** — German HAL Space, 300 dimensions
- **dewak100k_lsa** — German LSA Space, 300 dimensions
- **dewak100k_cbow** — German cbow space, 300 dimensions
- **de_wiki** — German cbow space, 400 dimensions
- **dewac_cbow** — German cbow space, 400 dimensions
- **itwac_cbow** — Italian cbow space, 400 dimensions
- **es_cbow** — Spanish cbow space, 400 dimensions
- **hr_cbow** — Croatian cbow space, 300 dimensions

Feel free to contact me if you need any semantic spaces not listed here
(for example in other languages).

## Descriptions of the semantic spaces

**TASA** [Download](https://drive.google.com/open?id=1PjSy9qyy7Sh3T9higCPqtgnG0_ffiuBC)<br>
*English LSA space, 300 dimensions*<br>
This LSA space was built from the TASA corpus, containing texts on a broad variety of topics.<br>
This space uses a variety of texts, novels, newspaper articles, and other information, from the TASA (Touchstone Applied Science Associates, Inc.) corpus used to develop The Educator's Word Frequency Guide.<br>
I am very thankful to the TASA folks for providing this corpus to the people at Boulder, Colorado, as well as to Morgen Bernstein, Donna Caccamise, Peter Foltz and the people from the NLP and LSA Research Labs in Boulder for providing me with this corpus.<br>
IMPORTANT: Calculations on this LSA Space will NOT give the same results as the [LSA homepage](http://lsa.colorado.edu), due to different parameter settings in the creation of the LSA space.<br>
See<br>
Günther, F., Dudschig, C., & Kaup, B. (2015). LSAfun – An R package for computations based
on Latent Semantic Analysis. *Behavior Research Methods, 47,* 930-944. [Link](https://link.springer.com/article/10.3758/s13428-014-0529-0) [Download](https://drive.google.com/open?id=1aplYVVJ1SLtO5Z04EY2ZJG16l-eAQLSO)<br>
for more information on this topic.<br>
This LSA space was built from 37,651 different documents and contains vectors for 92,393 different words.

**EN_100k** [Download](https://drive.google.com/open?id=1RZXoO1qCtiStd8BBjsik-5X8rSYYADIo)<br>
*English HAL space, 300 dimensions*<br>
Created from a 2.8 billion word corpus, which was created by concatenating the British National Corpus (BNC), the ukWaC corpus and a 2009 Wikipedia dump (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) and [here](http://www.natcorp.ox.ac.uk/)).<br>
This space was built using a HAL-like moving window model, with a window size of 5 (2 to the left, 2 to the right), with the 100k most frequent words in the corpus as row words as well as content (column) words for the co-occurrence matrix. A Positive Pointwise Mutual Information weighting scheme was applied, as well as a Singular Value Decomposition to reduce the space from 100k to 300 dimensions.<br>
This space contains vectors for 100,000 different words.

**EN_100k_lsa** [Download](https://drive.google.com/open?id=1cSkxluQW_ejkXbKrhLwjgLMajYZ5m7pz)<br>
*English LSA space, 300 dimensions*<br>
Created from a 2.8 billion word corpus, which was created by concatenating the British National Corpus (BNC), the ukWaC corpus and a 2009 Wikipedia dump. This corpus is divided into 5,386,653 individual documents (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) and [here](http://www.natcorp.ox.ac.uk/)).<br>
This space was created from a term-document matrix with the 100k most frequent words in the corpus as rows and the 5.4 million documents the corpus consists of as columns (as in LSA). Other than in LSA, a Positive Pointwise Mutual Information weighting scheme was applied instead of the standard log-entropy weighting (this should however not have a large influence on the results). As in standard LSA, an SVD was applied to reduce the space from the ~5.4 million dimensions to 300 dimensions.<br>
This space therefore vectors for 100,000 different words.

**EN_100k_cbow** [Download](https://drive.google.com/open?id=1JkDcCfFiUeCCAc45jlQ2GboSq8CHY5JI)<br>
*English cbow space, 300 dimensions*<br>
Created from a 2.8 billion word corpus, which was created by concatenating the British National Corpus (BNC), the ukWaC corpus and a 2009 Wikipedia dump (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) and [here](http://www.natcorp.ox.ac.uk/)).<br>
This semantic space was created using the cbow algorithm as implemented in the word2vec model ([Mikolov et al., 2013](https://arxiv.org/pdf/1301.3781)), using only the 100k most frequent words in the corpus as target and context words.<br>
The model parameters were as follows: A context window size of 5 words (i.e., 2 to the left, 2 to the right), and 300-dimensional vectors (negative sampling with k = 10, subsampling with t = 1e−5), corresponding to the second-best word2vec model examined by [Baroni et al. (2014)](http://www.aclweb.org/anthology/P14-1023).<br>
This space contains vectors for 100,000 different words.

**baroni** [Download (large file, 700 MB)](https://drive.google.com/open?id=1Tz_KR1lS1KGNaz2pbgZKnLOD7eFZWXuP)<br>
*English cbow space, 400 dimensions*<br>
The semantic space shown to produce the best empirical results by [Baroni et al. (2014)](http://www.aclweb.org/anthology/P14-1023). This semantic space is the "best predict vectors" space available [here](http://clic.cimec.unitn.it/composes/semantic-vectors.html), converted to .rda format.<br>
Created from a 2.8 billion word corpus, a concatenation of the British National Corpus (BNC), the ukWaC corpus and a 2009 Wikipedia dump (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) and [here](http://www.natcorp.ox.ac.uk/)). This semantic space was created using the cbow algorithm as implemented in the word2vec model ([Mikolov et al., 2013](https://arxiv.org/pdf/1301.3781)), using the parameter set shown to produce the best results by [Baroni et al. (2014)](http://www.aclweb.org/anthology/P14-1023): A context window size of 11 words (5 to the left, 5 to the right), and 400-dimensional vectors (negative sampling with k = 10, subsampling with t = 1e−5).<br>
This semantic space contains vectors for 300,000 different words

**ukwac_cbow** [Download (large file, 500 MB)](https://drive.google.com/open?id=14fWbCjfsIG2iXoU5hDCKGZ0ARSaYW47k)<br>
*English cbow space, 400 dimensions*<br>
Created from the 2 billion word ukWaC corpus (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) ). This semantic space was created using the cbow algorithm as implemented in the word2vec model ([Mikolov et al., 2013](https://arxiv.org/pdf/1301.3781)), using the following parameter set:<br>
A context window size of 5 words, and 400-dimensional vectors (negative sampling with k = 10, subsampling with t = 1e−5).<br>
This space contains vectors for all words that appear at least 50 times in the ukWaC corpus (211,358 different words).

**frwak100k** [Download](https://drive.google.com/open?id=1MDmFkV2atltomNHVcbLFQwdHiUMkb1Ij)<br>
*French HAL space, 300 dimensions*<br>
Created from the 1.6 billion word frWaC corpus (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) ) This space was built using a HAL-like moving window model, with a window size of 5 (2 to the left, 2 to the right), with the 100k most frequent words in the corpus as row words as well as content (column) words for the cooccurrence matrix. Accents were not removed (so *déjà* is stored as *déjà*). Words from this corpus were not lemmatized. A Positive Pointwise Mutual Information weighting scheme was applied, as well as a Singular Value Decomposition to reduce the space from 100k to 300 dimensions.<br>
This space contains vectors for 100,000 different words.

**dewak100k** [Download](https://drive.google.com/open?id=1QE4nhJkOTld2xxrqIt-yM-3SgIO_7Vqx)<br>
*German HAL space, 300 dimensions*<br>
Created from the 1.7 billion word deWaC corpus (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) ) This space was built using a HAL-like moving window model, with a window size of 5 (2 to the left, 2 to the right), with the 100k most frequent words in the corpus as row words as well as content (column) words for the cooccurrence matrix. A Positive Pointwise Mutual Information weighting scheme was applied, as well as a Singular Value Decomposition to reduce the space from 100k to 300 dimensions.<br>
This space contains vectors for 100,000 different words.

**dewak100k_lsa** [Download](https://drive.google.com/open?id=1689KFMiT-Aghn_omdBroDX8qTFokiZWd)<br>
*German LSA space, 300 dimensions*<br>
Created from the 1.5 million documents of the 1.7 billion word deWaC corpus metioned above (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) )<br>
This space was created from a term-document matrix with the 100k most frequent words in the corpus as rows and the 1.5 million documents the corpus consists of as columns (as in LSA). Other than in LSA, a A Positive Pointwise Mutual Information weighting scheme was applied instead of the standard log-entropy weighting (this should however not have a large influence on the results). As in standard LSA, an SVD was applied to reduce the space from the 1.5 million dimensions to 300 dimensions.<br>
This space contains vectors for 100,000 different words.

**dewak100k_cbow** [Download](https://drive.google.com/open?id=1orfH9aEdkSAhvsAa1UCzhc85WzKUzpIC)<br>
*German cbow space, 300 dimensions*<br>
Created from the 1.7 billion word deWaC corpus metioned above (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) )<br>
This semantic space was created using the cbow algorithm as implemented in the word2vec model ([Mikolov et al., 2013](https://arxiv.org/pdf/1301.3781)), using only the 100k most frequent words in the corpus as target and context words. The model parameters were as follows: A context window size of 5 words (i.e., 2 to the left, 2 to the right), and 300-dimensional vectors (negative sampling with k = 10, subsampling with t = 1e−5), corresponding to the second-best word2vec model examined by [Baroni et al. (2014)](http://www.aclweb.org/anthology/P14-1023).<br>
This space contains vectors for 100,000 different words.

**de_wiki** [Download (large file, 1.2 GB)](https://drive.google.com/open?id=1BDB3iZmqpOZ3bfMxpmiB9sg6aPJWfqmx)<br>
*German cbow space, 400 dimensions*<br>
Created from a 2017 German Wikipedia dump (1.5 billion words). This semantic space was created using the cbow algorithm as implemented in the word2vec model ([Mikolov et al., 2013](https://arxiv.org/pdf/1301.3781)), using the parameter set shown to produce the best results by : parameter set that was shown to produce the best empirical results by [Baroni et al. (2014)](http://www.aclweb.org/anthology/P14-1023): A context window size of 5 words, and 400-dimensional vectors (negative sampling with k = 10, subsampling with t = 1e−5).<br>
This space contains vectors for all words that appear at least 50 times in the Wikipedia corpus (526,004 different words).

**dewac_cbow** [Download (large file, 840 MB)](https://drive.google.com/open?id=1CnwyYFMUYY-lhb6jf5Mr4ttXTeggfl_w)<br>
*German cbow space, 400 dimensions*<br>
Created from a lemmatized version of the 1.7 billion word deWaC corpus (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) ). This semantic space was created using the cbow algorithm as implemented in the word2vec model ([Mikolov et al., 2013](https://arxiv.org/pdf/1301.3781)), using the following parameter set: A context window size of 5 words, and 400-dimensional vectors (negative sampling with k = 10, subsampling with t = 1e−5).<br>
This space contains vectors for all words that appear at least 50 times in the deWaC corpus (342,720 different words).

**itwac_cbow** [Download](https://drive.google.com/open?id=1Azr0p6fnSdiOlmuGYMS9rlwjgpQGlIqr)<br>
*Italian cbow space, 400 dimensions*<br>
Created from the 2 billion word itWaC corpus (see [here](http://wacky.sslmit.unibo.it/doku.php?id=corpora) ). This semantic space was created using the cbow algorithm as implemented in the word2vec model ([Mikolov et al., 2013](https://arxiv.org/pdf/1301.3781)), using the following parameter set:<br>
A context window size of 5 words, and 400-dimensional vectors (negative sampling with k = 10, subsampling with t = 1e−5).<br>
This space contains vectors for all words that appear at least 50 times in the itWaC corpus (175,266 different words).

**es_cbow** [Download](https://drive.google.com/open?id=1VOMDJjgiNLJbB_lCJmyOHQq3w1ipxpNd)<br>
*Spanish cbow space, 400 dimensions*<br>
Created from a lemmatized version of the 1.5 billion word OpenSubtitles 2018 Spanish corpus (see [http://www.opensubtitles.org/](http://www.opensubtitles.org/)).<br>
This semantic space was created using the cbow algorithm as implemented in the word2vec model ([Mikolov et al., 2013](https://arxiv.org/pdf/1301.3781)), using the following parameter set: A context window size of 5 words, and 400-dimensional vectors (negative sampling with k = 10, subsampling with t = 1e−5).<br>
This space contains vectors for all words that appear at least 50 times in the OpenSubtitles 2018 Spanish corpus (92,796 different words).

**hr_cbow** [Download](https://drive.google.com/open?id=1MDob9kiCah9CYmdnehm2I0mBd7L1EAlZ)<br>
*Croatian cbow space, 300 dimensions*<br>
Created from the 707 million word OpenSubtitles 2018 Croatian corpus (see [http://www.opensubtitles.org/](http://www.opensubtitles.org/)). This semantic space was created using the cbow algorithm as implemented in the word2vec model ([Mikolov et al., 2013](https://arxiv.org/pdf/1301.3781)), usingthe following parameter set:<br>
A context window size of 5 words, negative sampling with k = 10, subsampling with t = 1e−5. This space has 300 instead of 400 dimensions since the source corpus was only about half as large as the corpus used by Baroni et al. (2014).<br>
Note: Apparently, R struggles with the Croatian characters **č**, **ć** and **đ**, which aren't part of its UTF-8 code. R just replaces them with a regular c and d, respectively. To keep these characters identifiable, I replaced them in the row.names of the semantic space, using the following scheme:<br>
č >> \_c\_<br>
ć >> \_c2\_<br>
đ >> \_d\_<br>
If you would rather have them replaced with a regular c and d, use the R gsub() command on the row.names of the semantic space:<br>
`rownames(hr_cbow) <- gsub(rownames(hr_cbow),pattern="_c_",replacement="c")`<br>
`rownames(hr_cbow) <- gsub(rownames(hr_cbow),pattern="_c2_",replacement="c")`<br>
`rownames(hr_cbow) <- gsub(rownames(hr_cbow),pattern="_d_",replacement="d")`<br>
You can of course use any replacement you want here.<br>
This space contains vectors for all words that appear at least 50 times in the OpenSubtitles 2018 Croatian corpus (184,979 different words).
