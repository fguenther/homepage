---
title: ViSpa (Vision Spaces)
summary: "Vision-based semantic spaces: an online tool and downloadable representations."
nav_order: 3
parent: software-resources
kind: Web tool & download
permalink: /software-resources/vispa/
source: https://sites.google.com/site/fritzgntr/software-resources/vispa
---

## The ViSpa website

The simplest option to use Vision Spaces is our ViSpa website, which can be found at

[**http://vispa.fritzguenther.de**](http://vispa.fritzguenther.de)

## Downloadable vision spaces

All the vision spaces provided here are available in the .rda format for R.

Load them into the R workspace using:

`load("NAMEOFSPACE.rda")`

If you want to use the spaces outside of R, you can export them as .txt (or another preferred format) using the following command:

`write.table(NAMEOFSPACE,file="NAMEOFSPACE.txt",row.names=T,col.names=F)`

If you don't want to use R at all, you can contact me and I can provide you with the .txt files for the vision space

**The currently available vision spaces are:**

**IMG space, layer 6** [Download (large file, 480 MB)](https://drive.google.com/file/d/1kFAqWOM6SvWK-7BfpGXOwW39G4EkQpgV/view?usp=sharing)

*Representations for individual images, 400-dimensional vectors*

These representations are computed using a pre-trained version of the VGG-F model (Chatfield et al., 2014) provided in the MatConvNet toolbox for MATLAB (Vedaldi & Lenc, 2015). The VGG-F model is a deep convolutional neural network trained to predict labels for images. For this IMG space, we use layer 6 of the network, which has shown the best empirical performance in a set of large-scale evaluation studies. For computational mangeability, the dimensionality of these representations has been reduced from 4,096 to 400 using Singular Value Decomposition (which leaves all similarity values obtained from these representations virtually unchanged).

See the [help package of the vispa website](https://vectorswebtool.eu.pythonanywhere.com/doc/help/) for more information.

This IMG space contains representations for 7,801 labelled image categories, with up to 21 different images per category:

- 16 different randomly-selected individual images (for example, LION_001 to LION_015 as well as LION_030). You can look up these images online; the links always look like this: [https://storage.googleapis.com/homepage_images/images/LION/LION_005.JPEG](https://storage.googleapis.com/homepage_images/images/LION/LION_005.JPEG)
- 5 additional different individual images (for example, LION_000Q, LION_025Q, LION_050Q, LION_075Q, LION_100Q) with different similarities to the protoype representation (see the description below). LION_100Q is the *most similar* image to the prototype representation, LION_000Q is the *least similar* image to the prototype representation, LION_025Q is the 0.25-percentile, and so on

**PRO space, layer 6** [Download](https://drive.google.com/file/d/1QgbEofw_AVoqDBTxpN8S2DGWo4xg9dYs/view?usp=sharing)

*Representations for visual prototypes, 400-dimensional vectors*

These representations are computed by averaging 100 to 200 IMG representations for images with a given label; for example, for the prototypical representation LION_PRO, representations for images labelled LION were averaged.

See the [help package of the vispa website](https://vectorswebtool.eu.pythonanywhere.com/doc/help/) for more information.

This PRO space contains representations for 7,801 labelled image categories, such as LION_PRO

**IMG_PRO space, layer 6** [Download (large file, 500 MB)](https://drive.google.com/file/d/1nxXqEUnTGgTCCw_MGBIr_nvtTVrvprOd/view?usp=sharing)

*Representations for individual images as well as visual prototypes, 400-dimensional vectors*

This is simply a concatenation of the IMG space and PRO space described above.
