---
layout: post
title: Git on Mac OS persistently uses HTTP proxy
categories: posts
tags: [Archived]
aliases: ['/posts/2013/04/10/git-on-mac-os-persistently-uses-http-proxy']
---

So I've been running into the problem off late on Mac OS when using an HTTPS proxy and then using git over https. After removing the proxy from Preferences, the http proxy still persists giving an error as seen below:

~~~
Cloning into 'Foo'...
error: Failed connect to github.com:5222; Connection refused while accessing https://github.com/jonalmeida/Foo.git/info/refs
fatal: HTTP request failed
~~~

It took me a while to figure this out since I figured this was a Mac OS problem where the proxy settings weren't being removed. The quick fix is to remove the HTTP proxy globally through git:

~~~ bash
git config --global --unset http.proxy
~~~

Alas! That's all it took!
