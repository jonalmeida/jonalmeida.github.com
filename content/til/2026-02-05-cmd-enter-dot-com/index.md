---
title: "CMD + Enter autocompletes a word with a .com TLD"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

This has apparently existed since the dawn of time in all browsers (except Safari?).

Entering a word into the address bar, and then using Cmd + Enter[^1] wraps the word with 'www.' in the front and '.com' and the end of it.

{{ image(path="search-word.png") }}

Pretty neat! I tried this with `nautil.us` but it didn't work and went straight to `https://nautil.us` in Firefox. There might be some logic to respect known TLDs.


[^1]: Control + Enter on Windows.
