---
title: "Auto-resolve Jujutsu conflicts with your AI agent"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["workflow", "mozilla"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

With Jujutsu, I've been able to work in multiple workstreams more efficiently than before. This means that if I'm working on multiple things, there is a higher likelihood of something going stale while I wait for a review or touch multiple files.
Dealing with [conflicts aren't so bad these days][0], however if I can automate the easy ones, why not?

This is the prompt I've been using with my agent whenever I have a list of changes that have conflicts and don't need me to participate actively on it.

```
Using the jj version control system, fix the conflicts that are in the changesets from `<start_rev>` to `<end_rev>`. Keep trying until there are no more "(conflict)" in the changesets between those two IDs.
```

[0]: https://jonalmeida.com/til/android-studio-jj-conflicts/
