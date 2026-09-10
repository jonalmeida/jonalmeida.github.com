---
title: "Move MOZ_OBJDIR outside of mozilla-central to speed up your IDE"
draft: true
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["mozilla", "workflow"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

In mozilla-central (the firefox monorepo), a default object store directory is created within the source directory. This is equivalent to the `build/` directory you would typically see in other projects.

While this is typically fine, I've found that Android Studio indexes these files and we don't (yet?) have the ability to inform it to not do so because an objdir needs to be evaluated from `MOZ_OBJDIR` first.

Over time, I ended up with these build directories that grew over time:

| Directory                           | Last touched | Size  | Files   |
| ----------------------------------- | ------------ | ----- | ------- |
| `obj-aarch64-unknown-linux-android` | 2025-11-04   | 29 G  | 113,116 |
| `objdir-desktop`                    | 2025-11-04   | 19 G  | 41,010  |
| `objdir-frontend`                   | 2026-09-09   | 6.3 G | 66,930  |
| `obj-aarch64-apple-darwin24.5.0`    | 2025-06-16   | 4 K   | 1       |

That's a lot to index! A way around this problem is to move the objdir out of the source directory and into something like `~/.mozbuild`:

```sh
mk_add_options MOZ_OBJDIR="$HOME/.mozbuild/objdirs/$(basename `pwd`)/objdir-frontend"
```

**Why make this so complicated?**

1. I use [workspaces](https://www.jj-vcs.dev/latest/working-copy/#workspaces), so each of those have their own project directory with a different name - I've only gone one level down, but you could try everything from `$HOME` upward.
2. You can have [multiple objdirs for various build types](https://github.com/emilio/mozconfigs/) depending on what you're working on.
3. On most build machines, the `.mozbuild` directory is fairly optimized to be a fast accessor on the filesystem; close to the rest of the build files.

Given the above, this is what my final `mozconfig` looks like:

```sh
# Build GeckoView/Firefox for Android:
ac_add_options --enable-application=mobile/android

# Targeting the following architecture.
# For regular phones, no --target is needed.
# For x86 emulators (and x86 devices, which are uncommon):
# ac_add_options --target=i686
# For newer phones or Apple silicon
ac_add_options --target=aarch64
# For x86_64 emulators (and x86_64 devices, which are even less common):
# ac_add_options --target=x86_64

# sccache will significantly speed up your builds by caching
# compilation results. The Firefox build system will download
# sccache automatically.
# This only works for non-artifact builds.
#ac_add_options --with-ccache=sccache

# Enable artifact builds.
ac_add_options --enable-artifact-builds

# Write build artifacts to..
BASE_OBJDIR="$HOME/.mozbuild/objdirs/$(basename `pwd`)"

## Full build dir
#mk_add_options MOZ_OBJDIR="$BASE_OBJDIR/objdir-droid"
#mk_add_options MOZ_OBJDIR="$BASE_OBJDIR/objdir-desktop"

## manager-mode; artifact builds
mk_add_options MOZ_OBJDIR="$BASE_OBJDIR/objdir-frontend"

# Auto-clobber; don't ask
mk_add_options AUTOCLOBBER=1
```
