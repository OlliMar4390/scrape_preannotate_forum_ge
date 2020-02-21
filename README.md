# scrape_preannotate_forum_ge

### Scrape the med1.de forum and preannotate some of the html elements for [brat](http://brat.nlplab.org/)

This script scrapes forum posts from [https://www.med1.de/forum/nierenerkrankungen/](https://www.med1.de/forum/nierenerkrankungen/).

It analyses the threads a bit so that you know which contain how many answers.

As it is made to create a corpus that works with the [brat](http://brat.nlplab.org/) annotation tool, some of the HTML elements are converted:

* links &rarr; URL, annotated as pic, pdf, button, userm (user mention) or link
* img &rarr; alt, annotated as img

White space is preserved with the option of avoiding more than one consecutive empty Lines.

Blockquotes are shown as such.

The user can create one file per post or one file per thread.
