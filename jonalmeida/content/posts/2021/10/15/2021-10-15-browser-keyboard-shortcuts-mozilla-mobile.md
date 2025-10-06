---
layout: post
title: Useful bookmark keywords for Firefox (mobile) development
categories: posts

---

Firefox has support for keyword search in the address bar, which is handy during development at Mozilla. There are often many sources of information to look through and being able to get to them efficiently will save you _a lot_ of time.

The [support documentation][0] has excellent examples of how this works, but here is a simple annotated image of what it does:

![][1]

Below are a list of keyword shortcuts I use on a daily basis. Many of them are related to mobile development, but there are other userful ones too. You can manually copy over to your bookmark manager the ones that might seem useful.

# Search Fox

Search Fox is another internal tool at Mozilla for code indexes across all of mozilla-central and particular it's branches, mozilla-mobile, rust and many others. Search Fox is a go because of how fast it is and with symbolic references to JS/Rust/C++, you can navigate quite easily around the place. There are a few keywords that I'd recommend here.

 - sf - regular indexes of mozilla-central.
 - sfm - search through mozilla-mobile repositories (this includes application-services too).
 - sff - search through the 68 release branch code. This is particularly useful for mobile because it's the last release of Fennec (old Firefox Mobile) if you want to compare implementations.

```

Name: Searchfox - mozilla-central
Keyword: sf
URL: https://searchfox.org/mozilla-central/search?path=&q=%s

Name: Searchfox - mozilla-mobile (Mobile)
Keyword: sfm
URL: https://searchfox.org/mozilla-mobile/search?path=&q=%s

Name: Searchfox - Fennec - mozsearch
Keyword: sff
URL: http://searchfox.org/mozilla-esr68/search?q=%s&path=

```

# Mercurial

Sometimes you want to look up a diff from a changeset in your browser.

```

Name: Search mozilla-central with revision (changeset) ID
Keyword: diff
URL: https://hg.mozilla.org/mozilla-central/rev/%s

```

# Github

Many of our mobile projects are on Github so having quick access to an issue or pull request is great. We currently work on Android Components, Fenix and Focus a lot, so these keywords let me get to an issue or pull request directly. For example, `aci 10000` for navigating to the 10,000 issue in Android Components.

```

Name: Github - Android Components - Issues/Pull Requests
Keyword: aci
URL: https://github.com/mozilla-mobile/android-components/issues/%s

Name: Github - Fenix - Issues/Pull Requests
Keyword: fbi
URL: https://github.com/mozilla-mobile/fenix/issues/%s

Name: Github - Focus - Issues/Pull Requests
Keyword: fci
URL: https://github.com/mozilla-mobile/focus-android/issues/%s

```

# Taskcluster

Taskcluster is our internal CI build system. When a build fails or when you want to wait for a build, you can grab the ID from a pull request or release.

```

Name: FirefoxCI - Navigate to a task item (Task ID)
Keyword: ti
URL: https://firefox-ci-tc.services.mozilla.com/tasks/%s

Name: FirefoxCI - Navigate to a task group (Group ID)
Keyword: gi
URL: https://firefox-ci-tc.services.mozilla.com/tasks/groups/%s

```

# Android / Chromium

It's common to want source references to Android sources or compare Chromium implementations as well.

```

Name: Chromium Android - Code Search (Chromium Reference)
Keyword: cr
URL: https://cs.chromium.org/search/?q=%s&sq=package:chromium&type=cs

Name: Android Source References
Keyword: ar
URL: https://cs.android.com/search?q=%s

```

[0]: https://support.mozilla.org/en-US/kb/how-search-from-address-bar
[1]: /images/20211015/keywords.png
