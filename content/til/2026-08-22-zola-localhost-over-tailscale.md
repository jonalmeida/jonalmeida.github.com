---
title: "Serving Zola over Tailscale"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["meta"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

When I'm traveling and I need to remote into personal or build machine I would have to do some wacky port-forwarding over SSH to expose a host port to my local port.

With Tailscale this is much easier to do when working with this Zola blog!

In one terminal, you need `tailscale serve` (ensure your Tailnet has it enabled):

```
tailscale serve 1111
```

This should give you a tunnel that forwards all traffic from your `localhost:1111` to a public DNS record, however you need to be on a machine connected to your tailnet for the address to resolve.

```
Available on the internet:

https://my-machine.tailmetothemoon.ts.net/
|-- proxy http://127.0.0.1:1111

Press Ctrl-C to exit.
```

With that setup, you now need to serve Zola to that endpoint and make sure that hostname is used for links to work:

```
zola serve --base-url https://my-machine.tailmetothemoon.ts.net --no-port-append
```

A couple of notes for the command above:
- `--base-url` - To make all the links on the site work. If you don't add this, Zola would point to `localhost:1111`.
- `--no-port-needed` - For similar reasons, you don't need the port if you have the base URL corrected. I've also found that the port can trip up some mobile browsers too that have poor URL validation. 🙃
- The `https://` at the beginning of the URL is important. This tells Zola to use HTTPS for the base url, otherwise it defaults to HTTP, and the Tailscale funnel only runs over HTTPS.
