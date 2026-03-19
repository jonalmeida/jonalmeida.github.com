---
title: "Jujutsu for git users (WIP)"
draft: false
taxonomies:
  tags: ["workflow"]
  categories: ["blog"]
extra:
  hide_table_of_contents: true

---



## Basics

You can use `jj` with any git repository that you have - it's optional to use. So if you start using `jj` but don't like it, you can go back to using `git` commands without a problem.

We can start off with 

- The `@` sign tells you where you currently are - it's your working copy.
- `new`
  - In Jujutsu, you have an empty new working commit with `jj new` you never have an uncommitted set, you keep working on it until your next `new` or move to a different commit. In git, as you start working you are in a dirty/uncommitted state, you finalize your set at the end.
- `describe`
  - Similar to git commit - except that you commit at the end. With describe, you can do it at anytime - while you're planning out work, during some changes, or to finalize it. It's a 
- `edit`
  - You can edit a previous item with work on top of it. It's like an interactive rebase.
  - Git does not have that. You would need to make another branch and/or cherry-pick some changes.
- `rebase` 
  - Rebases never fail - they are first class citizen to VCS.
  - You can get conflicts, but you aren't required to fix it to move on.
  - It's fast - it applies all the rebased changes in-memory before it writes it to disk - this means that Android Studio doesn't keep indexing while things are happening.
- `op log`
  - Gives you a record of what you did. This is unlike the `git reflog`, where a rebase would show you twenty entries in there. You can restore to anywhere here.
  - Another way to use `undo` or `redo`. 

## Advanced or mozilla-central workflows

* `absorb`
* Handling conflicts.
* `split`
* No branches.
* `moz-phab patch`
* `workspaces`
