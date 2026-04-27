---
title: "Rebase all WIPs to the latest upstream head"
date: 2025-10-07
updated: 2026-04-28T14:00:00-04:00
draft: false
taxonomies:
  tags: ["workflow", "mozilla"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

A small pet-peeve with fetching the latest main on jujutsu is that I like to move all my WIP patches to the new one. That's also nice because jj doesn't make me fix the conflicts immediately!

The solution from a co-worker (kudos to skippyhammond!) is to query all immediate decendants of the _previous_ main after the fetch.

```bash
jj git fetch
# assuming 'z' is the rev-id of the previous main.
jj rebase -s "mutable()&z+" -d main
```

~~I haven't learnt how to make aliases accept params with it yet, so this will have to do for now.~~

**Update**: After a bit of searching, it seems that today this is only possible by [wrapping it in a shell script][1]. Based on the examples in [the jj documentation][0] an alias would look like this:

**Update 2**: After some months of usage across multiple repositories, I've found it better to be clear with the destination since `main`, `trunk` or others can be tracked with a combination of repository aliases too.

```toml
[aliases]
# Update all revs to the latest main; point to the previous one.
hoist = ["util", "exec", "--", "bash", "-c", """
set -euo pipefail
jj rebase -s "mutable()&$1+" -d "$2"
""", ""]
```

You can use this to rebase all your WIPs like so:

```bash
$ jj hoist <prev_main> <current_main>
```

If my previous `main` revision was `kz`, this is what I would end up doing:

```bash
$ jj fetch origin
$ jj hoist kz main@origin
```

[0]: https://docs.jj-vcs.dev/latest/config/#aliases
[1]: https://github.com/jj-vcs/jj/discussions/7129#discussioncomment-13933358
