---
title: "SSH access to Github over HTTPS"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["workflow", "mozilla"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

While using guest wifi during travels, I was trying to fetch some changes from a github remote and my `git fetch` is over SSH which happens over port 22. Most (TCP?) ports are blocked on public or hotel wifi, so with some help[^1] I learnt that Github serves SSH over 443 too.

A simple ssh config fixes this:

```ssh-config
Host github.com
  HostName ssh.github.com
  Port 443
```

[^1]: Claude.
