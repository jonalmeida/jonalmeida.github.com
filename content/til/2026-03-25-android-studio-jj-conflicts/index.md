---
title: "Use Android Studio for resolving conflicts in Jujutsu"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["workflow", "mozilla"]
  categories: ["til"]
extra:
  hide_table_of_contents: true
---

You can use JJ's built-in editor for conflict resolutions, but I've found it difficult to follow. A recommendation from co-workers was to use [Meld][0] and that has worked quite well once I (begrudingly) accepted that I needed to download another single-purpose app.

Today, another co-worker [Andrey Zinovyev][1] found out that we can use Android Studio's (IntelliJ IDEA's really) built-in merge tool to resolve the three-way merge. This is more convenient for me since I spend most of my time here already, so using it as a general purpose merge editor for my work projects is quite nice.

```toml
[ui]
merge-editor = "studio"

[merge-tools.studio]
merge-args = ["merge", "$left", "$right", "$base", "$output"]
program = "/Users/jalmeida/Applications/Android Studio Nightly.app/Contents/MacOS/studio"
```

Presto!

{{ image(path="2026-03-25_1.png") }}

[0]: https://meldmerge.org/
[1]: https://www.linkedin.com/in/andreyzinovyev
