---
layout: post
title: CrunchBang Linux Initial Setup
category: posts

---

I recently bought a ThinkPad T420s since the battery of my Dell Studio started to slowly die on me. Hence, I decided to start afresh with the ThinkPad and move away from Ubuntu to [CrunchBang Linux][crunch] (abrev: #!) which was the first linux OS I ever used.  It's a minimalistic Debian Wheezy based distribution that doesn't waste any of your time setting up your computer and lets you get to what you want to do.
It's hardly resource hungry as well. From a cold a boot it uses ~400MB of RAM.

I spent the best part the day setting up everything to be the way I like it. So I thought I'd at least put it somewhere for reference later on.

### Conky
The first thing I saw when I booted my laptop was conky - time to get a neat looking conky script to show off those stats. I settled for a conky script that I found on the #! forums. There are plenty more on the [forum][conky], but I found this one more to my liking. You can download the conkyrc file [here][conkyrc] and the lua file [here][lua].

![alt text][conky_screenshot]<br>
My T420s needed a special fan controller with a configuration which is handled by [thinkfan][thinkfan].

### Adaptive screen colour correction
I came across a nifty application called [f.lux][f.lux] that essentially corrects the colours of your screen to be 'warmer' as the day moves towards the end. The idea behind it is to not allow you get tired from staring at your screen all day. Which in turn, would cause irregular sleep patterns. While flux works perfectly on CrunchBang, I prefer to use it's alternative [Redshift][redshift] for linux OSes and f.lux for Windows/Mac. To be honest, the only reason I do this is because I think the f.lux icon looks out-of-place on most linux window managers - personal preference really. Not to mention that redshift already exists in the repositories, so a simple `sudo apt-get install redshift` solves all your problems. The help pages explain how to use it, but I set redshift to 5000 in ~/.config/openbox/autostart so that it's enabled on boot: `redshift -O 5000`

### Sublime Text 2 (Text Editor)
I'm a big fan of Sublime Text, so this is a must on any computer I use. The linux builds are available as a tar ball so it doesn't integrate well out-of-the-box. Below are the terminal commands to extract it to /opt/ and create a desktop link that can be found with any application launcher you use:

~~~ bash

tar xf Sublime\ Text\ 2.0.1\ x64.tar.bz2
sudo mv Sublime\ Text\ 2 /opt/
sudo ln -s /opt/Sublime\ Text\ 2/sublime_text /usr/bin/sublime
sudo wget http://jonalmeida.com/assets/misc/sublime.desktop /usr/share/applications/sublime.desktop

~~~
<br>
This last part is optional if you want all your text files to open with Sublime Text.

~~~ bash

sudo sublime /usr/share/applications/defaults.list

~~~
<br>
Replace all occurrences of geany.desktop with sublime.desktop

### Application launcher
CrunchBang comes with a neat, minimalistic (like everything else) app launcher that lives on the bottom of your screen that you can access with Alt + F3. I like using app launchers, but the current keyboard short-cut just doesn't feel comfortable.

You can change it by going to Settings > Openbox > Edit rc.xml, or open ~/.config/openbox/rc.xml with any text editor and add the configuration below to activate the app launcher with Ctrl + Space:
{% highlight html %}
    <keybind key="C-space">
      <action name="Execute">
        <startupnotify>
          <enabled>true</enabled>
          <name>dmenu-bind</name>
        </startupnotify>
        <command>~/.config/dmenu/dmenu-bind.sh</command>
      </action>
    </keybind>
{% endhighlight %}
<br>

### Java
Unfortunately, Java isn't going away any time soon:

~~~ bash

sudo apt-get install openjdk-7-jre

~~~

### Muti-arch support
On most debian distributions I've tried, enabling multi-arch support was as easy as installing the ia32-libs, however there's more to it here.

I found the solution from biggenaugust on the #! forums. First run:

~~~ bash

dpkg --add-architecture i386

~~~
<br>
Then add `[arch=amd64,i386]` to each line of `/etc/apt/sources.list`<br>
It should look something like this:

~~~ bash

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

~~~
<br>

After that, run:

~~~ bash

sudo apt-get update
sudo apt-get dist-upgrade

~~~
<br>
This is going to install all the relevant i386 library packages. It varies in size, but it's usually around ~100-200MB and requires a reboot after this.

### Overview
I'm quite content with my current set-up and I haven't had the need to make any changes to anything so far. Send me a message if there's anything that needs updating or if you might need to clarify something.


[crunch]: http://crunchbang.org
[conky]: http://crunchbang.org/forums/viewtopic.php?pid=556
[conkyrc]: /assets/code/conkyrc
[lua]: /assets/code/conky_lua.lua
[conky_screenshot]: /images/20130324/conky.png
[thinkfan]: http://thinkfan.sourceforge.net
[f.lux]: http://stereopsis.com/flux
[redshift]: http://jonls.dk/redshift
