---
title: "Migrating from Jekyll to Zola"
time: 2025-10-05
taxonomies:
  tags: ["blog"]
  categories: ["article"]
extra:
  hide_table_of_contents: false
---

I did it! 🙌

## Why

I found it tedious to maintain a Jekyll site and the various plugins that you needed for what I believe should be the built-in behaviour.

On new machines, I found myself using a [Docker image](https://github.com/BretFisher/jekyll-serve) for building the site locally until it eventually didn't work anymore.

## Preserving hard-links

Migrated the old Jekyll blog with help from [Eugene Baichenko's writings and script](https://eugene-babichenko.github.io/blog/jekyll-to-zola/).

After some more research, I learnt that Zola supports [`aliases`](https://www.getzola.org/documentation/content/page/) which lets you preserve your hard-links without needing to build the directory structure required to keep those links.
Aside, I haven't found the Zola documentation to be spectacular so it took me a bit to understand what aliases were and how to use them - I came across [the original issue to support aliases](https://github.com/getzola/zola/issues/86) which linked to the Hugo docs which told me what I needed to know. I'm also not complaining too much since this is a community-driven project; happy to use it's used by big players like [Fastmail](https://zola.discourse.group/t/allow-html-instead-of-md-for-pages-and-sections/149) too so maybe this is something where more corps can support too.

## Preserved page highlighting

Zola happily seems to support YAML as a frontmatter, so for legacy posts, I didn't need to update the format and instead just include the new properties where needed (e.g. disabling table of contents on certain posts). Along the way, I also learnt that [YAML supports references and inheritance](https://quickref.me/yaml.html) - wild stuff.

Existing syntax highlighting is also preserved and at most, I needed to update the language shortcodes to match Zola's (e.g. `objc` to `m`). In miscellaneous posts I seemed to have used Liquid templating, but that too wasn't hard to search-and-replace.

## Incremental migration from Jekyll

Doing the actual migration required slowly changing things over in my spare time. Starting off the blog in a sub-directory `/jonalmeida` first to get everything working there. Finally, removing the existing blog from the root directory and moving the contents of `/jonalmeida` into the root.
