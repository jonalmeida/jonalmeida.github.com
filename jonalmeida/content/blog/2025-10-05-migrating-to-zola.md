---
title: "Restarting this blog & migrating to Zola"
time: 2025-10-05
taxonomies:
  tags: ["blog"]
  categories: ["article"]
extra:
  hide_table_of_contents: false
---

I did it - finally restarted this blog! 🙌

## Why

I'll keep this short - there are others who are more expressive and have [shared][zola-0] [their][zola-1] [opinion][zola-2] on everything Zola does for them - go read those instead. Here is the shortform for me.

I found it tedious to maintain a Jekyll site and the various plugins that you needed for what I believe should be the built-in behaviour.

On every new machine I used, I found myself using a [Docker image](https://github.com/BretFisher/jekyll-serve) for building the Jekyll site locally so I could get the magic combination correct to have it always working, until it eventually didn't work anymore.

## Preserving hard-links

I started with trying to look out for a way to migrate my existing Jekyll posts while also preserving the hard-links to them. I came across [Eugene Baichenko's writings and script](https://eugene-babichenko.github.io/blog/jekyll-to-zola/) which I used and got myself up and running in no time.

After some more research, I learnt that Zola supports [`aliases`](https://www.getzola.org/documentation/content/page/) which lets you preserve your hard-links without needing to build the directory structure required to keep those links. Those links just redirect to the new Zola ones, which was fine by me.

## Preserving page highlighting

Zola happily seems to support YAML as a frontmatter, so for legacy posts, I didn't need to update the format and instead just include the new properties where needed (e.g. disabling table of contents on certain posts). Along the way, I also learnt that [YAML supports references and inheritance](https://quickref.me/yaml.html) - wild stuff.

Existing syntax highlighting is also preserved and at most, I needed to update the language shortcodes to match Zola's (e.g. `objc` to `m`). In miscellaneous posts I seemed to have used Liquid templating, but that too wasn't hard to search-and-replace.

## Incremental migration from Jekyll

Doing the actual migration required slowly changing things over in my spare time. Starting off the blog in a sub-directory `/jonalmeida` first to get everything working there. Finally, removing the existing blog from the root directory and moving the contents of `/jonalmeida` into the root.

## Final thoughts

It seems like most of the audience for Zola are coming from other Static Site Generators platforms.

I haven't found the Zola documentation to be spectacular so it took me a bit to understand what aliases were and how to use them - I came across [the original issue to support aliases](https://github.com/getzola/zola/issues/86) which linked to the Hugo docs that eventually told me what I needed to know. I'm also not complaining too much since this is a community-driven project; happy to use it's used by big players like [Fastmail](https://zola.discourse.group/t/allow-html-instead-of-md-for-pages-and-sections/149) too so maybe this is something where more corps can support too.

In another case, I moved to Zola because I wanted separate feeds for each tag and I couldn't figure out to get this to work even though I had already enabled it with this block:

```toml
taxonomies = [
    {name = "categories", feed = false},
    {name = "tags", feed = true},
]
```

This must be my own shortsightedness though, because it seems [obvious to others](https://tilde.club/~passthejoe/zola/blog/zola-tag-category-feeds/index.html).


All in all though, I'm quite happy with where I've gotten to and I find the Zola and Tera templating combination far less intimidating.

Let's see where this takes me.

[zola-0]: https://simeon.staneks.de/en/posts/zola-the-holy-grail-of-ssg/
[zola-1]: https://daudix.one/blog/zola-vs-jekyll/
[zola-2]: https://www.kytta.dev/blog/one-week-with-zola/
