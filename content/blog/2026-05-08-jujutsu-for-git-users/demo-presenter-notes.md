---
title: "jj presentation - cheat sheet"
draft: false
date: 2026-05-08
taxonomies:
  tags: ["workflow"]
  categories: ["blog"]
extra:
  hide_table_of_contents: false
---

# jj presentation - cheat sheet

A throwaway Calculator app in `mobile/android/fenix/.../calculator/` provides the demo material. Re-run between demos to reset:

```
bash artifacts/jj-demo-setup.sh
```

## The starting stack

```
@  wip small fixes (absorb me)    ← uncommitted: two 1-line fixes
○  E: Add equals and clear logic
○  D: Add operator buttons and tighten outer padding   ← split target
○  C: Add digit buttons                                ← absorb target #2
○  B: Add CalculatorViewModel with display state       ← absorb target #1
○  A: Add CalculatorScreen scaffold
◆  main
```

The wip change contains two unrelated 1-line edits:
- `CalculatorViewModel.kt`: `MutableStateFlow("")` → `MutableStateFlow("0")`
- `CalculatorScreen.kt`: `Arrangement.spacedBy(4.dp)` → `8.dp` in `DigitRow`

Each line was last touched in a different commit, so absorb can route them.

---

## Demo 1 - `jj split`

Commit D bundles two unrelated changes: an operator-row feature (across both .kt files) and a one-line outer-padding tweak. Split them apart.

```
jj edit  <D's change id>     # or: jj edit @--   if wip is on top of E
jj split
```

The diff editor opens with all of D's hunks. Keep just the operator-row hunks in the first commit, leave the padding tweak for the second. Save -> two commits. Re-describe the second:

```
jj describe -m "DEMO: Tighten outer padding"
```

`jj log -r main..` shows D replaced by two narrowly-scoped commits.

## Demo 2 - `jj absorb`

Back to top of stack, with the wip fixes uncommitted:

```
jj edit @         # if you're not already there
jj diff           # show the two tiny hunks
jj absorb
```

Output:

```
Absorbed changes into 2 revisions:
  <C>  DEMO: Add digit buttons
  <B>  DEMO: Add CalculatorViewModel with display state
```

`jj log` to show the wip change is gone, its hunks now live in B and C where they belong. No interactive picking, no commit reordering.

## Demo 3 - `jj rebase`

Show the "pull a commit out of the middle of the stack" superpower. Without conflicts first, move D after E:

```
jj rebase -r <D> --insert-after <E>
```

D pops up to the top of the stack, E sinks below it, descendants auto-rebase. No conflict because D and E touch disjoint lines.

(Reset before the next demo if you want a clean log.)

## Demo 4 - Conflicts via rebase

Try the rebase that *can't* clean up automatically: move E (which adds
`OperatorRow(...)`-adjacent equals/clear UI) to before C (which adds the
digit buttons that E's diff context relies on).

```
jj rebase -r <E> --insert-before <C>
```

jj reports:

```
New conflicts appeared in 2 commits:
  <C> (conflict) DEMO: Add digit buttons
  <E> (conflict) DEMO: Add equals and clear logic
```

`jj log` shows the two affected commits marked `×`. The stack stays in place - this is the killer property: **conflicts are first-class state, not a mode you have to escape from**. You can keep working, look at sibling commits, run `jj diff`, etc.

To resolve:

```
jj new <E>                 # step onto a child of the first conflicted commit
jj resolve --list          # see the conflicted paths
jj resolve                 # opens the configured merge tool
                           # or edit conflict markers in place, then `jj squash`
```

After resolving E, the second conflict (in C) often resolves automatically
because jj re-propagates the resolution down the stack.

---

## Useful surrounding commands

- `jj log -r 'main..@'` - just the demo stack
- `jj op log` - every operation you've run; `jj op restore <id>` to undo anything
- `jj diff -r <change>` - show one commit's diff
- `jj evolog -r <change>` - history of one logical change as you've reshaped it
