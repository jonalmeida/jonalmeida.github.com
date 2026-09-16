---
title: "Checkout a Github pull request from one-off contributions"
draft: false
updated: 2026-09-16T01:38:50.378-04:00
taxonomies:
  tags: ["mozilla", "workflow"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

EDIT: Updated to reference `gh` correctly. Thanks flod!

Sometimes on Github, I need to fetch a patch from a fork I don't typically see everyday so I can try it out locally. I use the line at the top of the patch which has a copy button next to it because it's convenient.

{{ <image path="image-1.png" /> }}

The common steps for this are:

1. Click the contributor's branch and go to their github fork repository.
2. Copy the repository link.
3. Add a new git remote with an alias (typically their username).
4. `git fetch <alias>`
5. `git checkout <alias>/<branch>`

Here is a one-liner for it that you can add to your `gitconfig`:

```toml
[alias]
  co = "!f() { PNAME=$(basename `git rev-parse --show-toplevel`); OWNER=$(echo $1 | cut -d':' -f1); BRANCH=$(echo $1 | cut -d':' -f2); git fetch git@github.com:$OWNER/$PNAME.git $BRANCH; git checkout FETCH_HEAD; }; f"
```

You might ask, why do all of this when the github `gh` CLI does this for you?
While it does simplify some tasks, I wanted a solution that was independant to a specific git host. The `git@github.com` remote that is used in the alias can be changed or made configurable if desired. This is something that I wouldn't be able to do with platform-dependant `gh`.

The fetch also works well with `jj` too because the fetch and checkout remain headless.

---

Formatted and commented, it looks less intimidating:

```sh
f() {
  # Get the repository name from your checkout (assuming it is the
  # original directory name as the remote).
  PNAME=$(basename `git rev-parse --show-toplevel`);

  # Parse out the fork's owner.
  # Example: `<owner>:<branch>`
  OWNER=$(echo $1 | cut -d':' -f1);

  # Parse out the branch name.
  # Example: `<owner>:<branch>`
  BRANCH=$(echo $1 | cut -d':' -f2);

  # Do a fetch of that particular branch using the extracted
  # information from above.
  # This assumes the remote is hosted on github.
  git fetch git@github.com:$OWNER/$PNAME.git $BRANCH;

  # Checkout using the alias `FETCH_HEAD` which git provides.
  git checkout FETCH_HEAD;
};

# Execute the function!
# It's easier to build a function that holds variables and execute
# rather than in-line it.
f
```

{{ <comments host="mindly.social" username="jonalmeida" id={117279142568496801} /> }}
