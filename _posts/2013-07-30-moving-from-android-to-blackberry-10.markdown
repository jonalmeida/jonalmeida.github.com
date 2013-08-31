---
layout: post
title: Moving from Android to BlackBerry 10
category: posts

---

This is going to be a ongoing post that's updated over time since I'm sure I'll run into things I need to add later.

First, it's worth mentioning that I hated BlackBerry - I didn't understand why people even used them when they were popular, and I didn't understand why people used them when they were not. Ironically, I had to use one at work and though I despised it at first, I tried to keep an open mind about it. Which seems to have made all the difference because I can't seem to not use one. I'm not even talking about what BlackBerry 10 is now, I mean during the BBOS times.

Now the other side of that coin is that during the period of hate, I loved the idea of Android (and still do to some extent) being open, easy to use, free to develop on, etc. What's there to hate?
My recent annoyance with it, is that it isn't dependable. It's fragmented, the OS is still left to manufacturers to update (Nexus devices excluded), and if the updates don't make it, you're pretty much left on your own. I've gone through an HTC Desire to a Galaxy Nexus and they were both great phones in their day and age, but I couldn't help but notice how quickly they degraded to being slow and useless within a time frame of a year at most.
Anywho, the point being: I wanted speed, support and spoons (because I can't think of another word starting with 'S').

In order to make my switch, I took a good look at my Q10 and Galaxy Nexus to weigh them out equally to see if it was even remotely possible to make the switch over.

I started off by comprising a list of apps that I had on my Galaxy Nexus that I couldn't live without:

  - Evernote
  - Email account support	
  - WhatsApp
  - Google Authenticator
  - Ingress
  - Text messaging backups to Gmail
  - Camera picture sync

**Evernote and email account** support was easy since Evernote support is built into the notes application that comes with the phone and email support... do I really need to explain this part? It's a BlackBerry, it was made for email.

**WhatsApp**: I don't really use as much, but it's available in the BlackBerry app store.

**Google Authenticator** is an app I use almost religiously for two-factor authentication of my Google account, SSH login, Evernote, anything else you fancy that needs that level of authentication. The problem was that once you have your account setup on Google Authenticator for your Android, you can't get that setup code again.<br>
Fair enough, but I was sure I could figure this out. First I needed the application to begin with. I was able to get that from apk2bar.org and sideload it onto my device fairly easily.<br>
On my Galaxy Nexus, I logged into an adb shell and swooped around for the application data files. After perusing the internet as well, I found that the secret key is stored in a sqlite file in `/data/data/com.google.android.apps.authenticator2/databases/databases` <br>
I downloaded the file to my computer and opened it up in sqlite3 to retrieve the key:
{% highlight html %}
sqlite3 ./databases
select * from accounts;
{% endhighlight %}<br>
You can now use that secret key that you can add on your other Google Authenticator. You can also use the 'Move to a different phone' option in your Google Account settings to move your account, but I wasn't too happy with that option when I found out that it would break all your existing applications specific passwords that you had given access.

For **camera picture syncing** that wasn't too hard as well since this features seems to be supported using Box (which also gives you 50GB of online storage while signing up), but what I really wanted was to have it sync Dropbox. Once again, I went the help of the built-in Android Player and I was able to use the Android version of Dropbox to sync all those cat pictures from my phone to a (safe?) remote location.

**Text Message sync** took a bit more googling, but I eventually came across an application called [SyncLion][synclion] which has almost all the features SMS Backup+ currently has. Since not all apps can run as a service, it lacks the fine feature of auto-sync which I adore oh-so-much. When this comes, it will be well worth the $2.99 it currently costs on BB World.

Alas, **Ingress** is the only application I can't get on my Q10! Ingress is an augmented reality, location based game created by Google. It's more interesting to play it than to explain so I'll leave that up to you to research. 
The problems with trying to sideload the android app is that the Android Player doesn't support Google account APIs, for legal reasons I pressume. Authenticating using your Google account is the only way to go about it, so for now I'm stuck..

Refs: [How-To Geek][howtogeek]


[howtogeek]: http://www.howtogeek.com/130755/how-to-move-your-google-authenticator-credentials-to-a-new-android-phone-or-tablet/
[synclion]: http://appworld.blackberry.com/webstore/content/20384391/