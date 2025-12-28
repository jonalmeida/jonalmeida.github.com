---
title: "Rebase all WIPs to the new main"
date: 2025-10-07
draft: false
taxonomies:
  tags: ["workflow"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

A small pet-peeve with fetching the latest main on jujutsu is that I like to move all my WIP patches to the new one. That's also nice because jj doesn't make me fix the conflicts immediately!

The solution from a co-worker is to query all immediate decendants of the _previous_ main after the fetch.

```sh
jj git fetch
# assuming 'z' is the rev-id of the previous main.
jj rebase -s "mutable()&z+" -d main
```

I haven't learnt how to make aliases accept params with it yet, so this will have to do for now.
