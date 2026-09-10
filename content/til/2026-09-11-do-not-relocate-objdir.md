---
title: "Perf wins from relocating MOZ_OBJDIR have a dev experience cost"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["mozilla", "workflow"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

This is the opposite of what I wanted to write about: relocating your MOZ_OBJDIR outside of your source directory will make your IDE faster.

In mozilla-central (the firefox monorepo), a default object files directory is created within the same source directory. This is equivalent to the `build/` directory you would typically see in other projects.

While this is typically fine, I've found that Android Studio indexes many of these files and that can be slow when you're not working across all the layers in Gecko and Firefox. I ended up with these build directories that grew over time:

| Directory                           | Last touched | Size  | Files   |
| ----------------------------------- | ------------ | ----- | ------- |
| obj-aarch64-unknown-linux-android   | 2025-11-04   | 29 G  | 113,116 |
| objdir-desktop                      | 2025-11-04   | 19 G  | 41,010  |
| objdir-frontend                     | 2026-09-09   | 6.3 G | 66,930  |
| obj-aarch64-apple-darwin24.5.0      | 2025-06-16   | 4 K   | 1       |

That's a lot to index! I figured a way around this problem is to move the OBJDIRs out of the source directory and into something like `~/.mozbuild`:

```sh
mk_add_options MOZ_OBJDIR="$HOME/.mozbuild/objdir-frontend"
```

While this does speed up IDE indexing, it's at the cost of developer experience, because now our generated code (e.g. `FxNimbus`) shows up as red symbols everywhere.

_[insert sad trombone sound clip]_

I'm uncertain if trimming what we index in these OBJDIRs is worth a large enough performance win, so for now I'll ensure I clean-up my stale copies which I'm not actively using.
