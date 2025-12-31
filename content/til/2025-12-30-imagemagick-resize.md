---
title: "Preserve image scale with ImageMagick"
date: 2025-12-30
draft: false
taxonomies:
  tags: ["blog"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

Resizing images with `imagemagick` is straightforward even if the tool comes off intimidating.

```bash
magick input.jpg -resize 1024x output.jpg
```

The `1024x` is a "geometry" argument that says, "make the image 1024 pixels width for any height". This preserves the scale for the image without needing to compute it yourself. 

You can also do the same for the height as well.

```bash
magick input.jpg -resize x768 output.jpg
```

There are more details on the full geometry argument at [the ImageMagick documentation site][0] ([alternative link][1]).

If you want to perform this in bulk, there seems to be built-in wildcard support or wildcard shell handling for it:

```bash
$ magick *.jpg -resize x768 image.jpg
$ ls
picture.jpg
another.jpg
onemore.jpg
image-0.jpg
image-1.jpg
image-2.jpg
```



[0]: https://imagemagick.org/script/command-line-processing.php#geometry
[1]: https://imagemagick.org/Magick++/Geometry.html "Alternative ImageMagick link to API docs."
