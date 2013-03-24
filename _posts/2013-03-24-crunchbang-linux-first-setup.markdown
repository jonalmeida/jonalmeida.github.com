---
layout: post
title: CrunchBang Linux First Setup
category: posts

---

I recently bought a ThinkPad T420s since the battery of my Dell Studio started to slowly die on me. Hence, I decided to start afresh with the ThinkPad and move away from Ubuntu to [CrunchBang Linux][crunch] (abrev: #!) which was the first linux OS I ever used.  It's a minimalistic Debian Wheezy based distribution that doesn't waste any of your time setting up your computer and lets you get to what you want to do.
It's hardly resource hungry as well. From a cold a boot it uses ~400MB of RAM.

I spent the best part the day setting up everything to be the way I like it. So I thought I'd at least put it somewhere for reference later on.

### Conky
The first thing I saw when I booted my laptop was conky - time to get a neat looking conky script to show off those stats. I settled for a conky script that I found on the #! forums. There are plenty more on the [forum][conky], but I found this one more to my liking. You can download the conkyrc file [here][conkyrc] and the lua file [here][lua].

![alt text][conky_screenshot]


### Muti-arch support
On most debian distributions I've tried, enabling multi-arch support was as easy as installing the ia32-libs, however there's more to it here.

I found the solution from biggenaugust on the #! forums. First run:
{% highlight html %}
$ dpkg --add-architecture i386
{% endhighlight %}<br>

Then add `[arch=amd64,i386]` to each line of `/etc/apt/sources.list`<br>
It should look something like this:
{% highlight html %}
## CRUNCHBANG
## Compatible with Debian Wheezy, but use at your own risk.
deb [arch=amd64,i386] http://packages.crunchbang.org/waldorf waldorf main
# deb-src [arch=amd64,i386] http://packages.crunchbang.org/waldorf waldorf main

## DEBIAN
deb [arch=amd64,i386] http://http.debian.net/debian wheezy main contrib non-free
# deb-src [arch=amd64,i386] http://http.debian.net/debian wheezy main contrib non-free

## DEBIAN SECURITY
deb [arch=amd64,i386] http://security.debian.org/ wheezy/updates main
# deb-src [arch=amd64,i386] http://security.debian.org/ wheezy/updates main

{% endhighlight %}<br>

After that, run:

{% highlight html %}
$ sudo apt-get update
$ sudo apt-get dist-upgrade
$ sudo apt-get dist-upgrade
{% endhighlight %}<br>

This is going to install all the relevant i386 library packages. It varies in size, but it's usually around ~100-200MB and requires a reboot after this.

[crunch]: http://crunchbang.org
[conky]: http://crunchbang.org/forums/viewtopic.php?pid=556
[conkyrc]: /assets/code/conkyrc
[lua]: /assets/code/conky_lua.lua
[conky_screenshot]: /images/20130324/conky.png