---
title: "Don't credit Claude for patches that you submit for code review"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["workflow"]
  categories: ["blog"]
extra:
  hide_table_of_contents: true
---

Spicy topic, right?

I haven't used Claude Code nearly as much as I could to be honest, but enough to have an opinion on it.

Adding credits or notifying the reviewers that you used an AI agent was useful for a few reasons:
 1. This patch was written with support from an agent, and it might be useful context during a code review from a human (e.g. asking them to take extra care on the correctness of the patch).
 2. To be a good citizen and say where the work originated from.

Doing this now for those reasons seems unproductive. In the same order as the above, I'd say:
 1. What you submit for review shouldn't matter how it came to be, even if it was a script someone else wrote that generated the updated files for you to check-in. _You_ are submitting those changes with your name and therefore should take responsibility for what is submitted. If Claude generated slop, it was you that submitted it without vetting it and it put your name on it, so your code is slop.
 2. There is more hostility online when you use AI tools. I can understand the frustration that some folks have had, but not everyone is abusing the tools and causing harm. It's hard to avoid being lumped into the same bucket, and being open about your workflow puts a target on your back, unfortunately.

Maybe this is comes across as obvious for others, but it wasn't for me, and I needed to ramble somewhere.

