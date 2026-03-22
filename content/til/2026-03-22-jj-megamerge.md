---
title: "Create new revisions in Jujutsu with multiple heads"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["workflow", "mozilla"]
  categories: ["til"]
extra:
  hide_table_of_contents: true
---

It was one of those "ah ha!" moments for me when I finally used it. Chris Krycho [covers the concept of megamerges][0] with this diagram:

```
       m --- n
      /       \
a -- b -- c -- [merge] -- [wip]
      \       /
       w --- x
```

I've found a more realistic example that best relates to my natural workflow: implementing feature (A) benefitted from having the changes of another tooling patch upgrade (B), that lead to discovering and fixing a bug (C).


```
      (B)
       m ----- n
      /         \           (A)
a -- b --------- [merge] --- y -- z
      \                     /      \                (C)
        -------------------         ----- [merge] -- w -- x
        \                                /
          -------------------------------
```

In this case, trying to separate these into distinct streams of work is quite logically, but we also don't need to leave them unlinked so that they can benefit from each other.

This is what my `jj log` ended up looking like:

```jj
@  oppmsuvz jxxxxxxxxxxxx@gmail.com 2026-03-22 00:34:10 firefox@ 05259417
│  Bug xxxxxxx - Simplify the tests
○  ultowtnr jxxxxxxxxxxxx@gmail.com 2026-03-22 00:34:04 100c4cce
│  Bug xxxxxxx - Include private flag in ShareData
○    lorusmuo jxxxxxxxxxxxx@gmail.com 2026-03-21 20:19:30 905b0460
├─╮  (empty) (no description set)
│ ○  sumqskuu jxxxxxxxxxxxx@gmail.com 2026-03-21 04:22:00 92f6028b
│ │  Add a new secret settings fragment
│ ○  oylmprpu jxxxxxxxxxxxx@gmail.com 2026-03-21 04:22:00 18931825
│ │  Create a new feature for receiving and sending commands.
│ ○  xrnnoonu jxxxxxxxxxxxx@gmail.com 2026-03-21 04:21:48 618020c7
╭─┤  (empty) (no description set)
│ ○  rqlyqqzx jxxxxxxxxxxxx@gmail.com 2026-03-19 17:20:20 c9b5323c
│ │  Bug xxxxxxx - Part 2: Create new android gradle module skill
│ ○  txvozpwz jxxxxxxxxxxxx@gmail.com 2026-03-19 17:20:13 cee18510
├─╯  Bug xxxxxxx - Part 1: Add new gradle example module
◆  pwsnmryn vxxxxxxxxxxxx@gmail.com 2026-03-18 13:21:47 main@origin fa20ce29
│  Bug xxxxxxx - Make my feature work for everyone
~
```

When I need to submit these, [moz-phab][[1] has support for specifying revset ranges with `moz-phab start_rev end_rev`. However, I can also use `jj rebase -s <rev> -d main@origin` to put out some try pushes to validate they still work separately - so far, no conflicts in this step.

[0]: https://v5.chriskrycho.com/journal/jujutsu-megamerges-and-jj-absorb/
[1]: https://pypi.org/project/MozPhab/
