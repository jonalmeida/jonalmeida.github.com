---
layout: post
title: Ubuntu 14.04 without Unity launcher
category: posts

---

Ubuntu 14.04 LTS recently launched so I decided to give it a spin on a spare SSD I had (I'm not a fan of desktop VMs). So far I'm really happy with everything, especially the polish that comes with it. On my T420s I get optimal battery performance and a level of speed I'm able to live with. The only thing I didn't want was the Unity launcher - it's a neat idea and I'm not a crazy rager who is out to kill everything new, but I just don't find myself using it _at all_ since Ubuntu 11.04.

There isn't any way to disable it entirely, but you can make it go away and never show up.

## Unity Tweak Tool

You're going to need Unity Tweak Tool which should be in Trusty third party repos:

``` bash
sudo apt-get install unity-tweak-tool
```

There are a couple of things you need to disable to stop the launcher from showing up when you mouse-over certain areas or certain key combinations:

- Unity -> Launcher
 - Auto-Hide: _ON_
 - Reveal Location: _Top Left Corner_
 - Reveal Sensitivity: _0%_
- Unity -> Web Apps
 - Integration prompts: _OFF_
 - Amazon: _UNCHECK_
 - Ubuntu One: _UNCHECK_

![image][1]
<br>

Disable the launcher from appearing when you press and hold the super key:

- Unity -> Additional
 - Show Launcher: _Disabled_


![image][2]

## Removing Unity Lens (Optional)

I didn't really see the point of keeping a bunch of Unity lenses. Even if I was going to re-enable the launcher, I was never going to use them. These are just a few of them that I had particularly no interest in them.

``` bash
sudo apt-get purge unity-lens-video unity-lens-music unity-scope-audacious unity-scope-clementine unity-scope-colourlovers unity-scope-gdrive unity-scope-gmusicbrowser unity-scope-gourmet unity-scope-guayadeque unity-scope-manpages unity-scope-musique unity-scope-openclipart unity-scope-tomboy unity-scope-yelp unity-scope-zotero unity-scope-musicstores
```

[1]: /images/20140508/1.png
[2]: /images/20140508/2.png