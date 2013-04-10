---
layout: post
title: Git on Mac OS persistently users HTTP proxy
category: posts

---

So I've been running into the problem off late on Mac OS when using an HTTPS proxy and then using git over https. After removing the proxy from Preferences, the http proxy still persists giving an error as seen below:

{% highlight html %}
Cloning into 'Foo'...
error: Failed connect to github.com:5222; Connection refused while accessing https://github.com/jonalmeida/Foo.git/info/refs
fatal: HTTP request failed
{% endhighlight %}<br>


It took me a while to figure this out since I figured this was a Mac OS problem where the proxy settings weren't being removed. The quick fix is to remove the HTTP proxy globally through git:
{% highlight html %}
git config --global --unset http.proxy
{% endhighlight %}<br>

Alas! That's all it took!
<br>