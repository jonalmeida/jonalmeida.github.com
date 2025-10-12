---
layout: post
title: Setting up ownCloud on Mac OS Mountain Lion to use via SSH
categories: posts
tags: [Archived]
aliases: ['/posts/2014/01/05/setting-up-owncloud']
---

I've been looking for a way to remotely access my media securely using ownCloud but I could never get myself to sit down and do it. Turns out that it's a bit of a hurdle on Mac OS because it [isn't officially supported][support]. 

## Setting up the web server
In Mountain Lion, Apple remove the option to easily start a web server from System Preferences -> Sharing. So instead we have to do it via Terminal.app, which if fine since we can setup a few more things from there as well.

First check where the server's root directory starts in:

~~~ bash

jonathan$ grep "DocumentRoot \"" /etc/apache2/httpd.conf
DocumentRoot "/Library/WebServer/Documents"

~~~
<br>
I preferred to change this to `/Library/WebServer/Sites` to make it more consistent, but I'll only refer to the default one in this post.

Uncomment the line `php5_module` in the `/etc/apache2/httpd.conf` to enable php5 since ownCloud requires it. It should look something like this:

![](/images/20140105/1.png)

Create a configuration that allows your user to access the web server.

~~~ bash

sudo vim /etc/apache2/users/`whoami`.conf

~~~
<br>
Add this configuration into the file:

~~~ html

<Directory "/Library/WebServer/Documents/">
     Options Indexes MultiViews
     AllowOverride All
     Order allow,deny
     Allow from all
</Directory>

~~~
<br>
Then start the server with:

~~~ bash

sudo apachectl start

~~~
<br>
If you didn't modify your DocumentRoot, going to `localhost` in your web browser will show "It Works!", otherwise, create a simple `index.html` file in your DocumentRoot directory just to verify it works.

![](/images/20140105/2.png)

## Installing ownCloud server

Go to the [ownCloud download page][download] and download the latest server as a tar file and extract the contents. You want to move the '/owncloud' directory to your DocumentRoot location `/Library/WebServer/Documents`.

Give the apache webserver the right ownership to the owncloud directory:

~~~ bash

sudo chown -R _www:_www /Library/WebServer/Documents/owncloud

~~~
<br>
You also need to create a `.htaccess` file at the DocumentRoot location with:

~~~ bash

Options FollowSymLinks

~~~
<br>
If all went well, you should now be able to setup an administrator account in ownCloud from your browser with `http://localhost/owncloud`. <br>
*Note: During the setup, you should change the data folder to another location under Advanced for security. I chose mine to be* `/Library/WebServer/owncloud/data`.

If you do change the data directory, remember to give that directory the same ownership so that it can be accessed as well:

~~~ bash

sudo chown -R _www:_www /Library/WebServer/owncloud/data

~~~
## Adding local server directories
I wanted to be able to add local directories that were part of my user files on my Mac. I found out that you can do that by installing the ownCloud app **External storage support**.
Then in the admin settings, setup a folder from there with the 'Configuration' field as the absolute path to the directory you want. When done, a green circle will show up, to confirm if the folder is accessible.

![](/images/20140105/3.png)
## Accessing via SSH
If you're behind a firewall or a local network, this web server won't be accessible past your LAN (which is how I wanted it). For those instances where I *did* want to access it remotely, I wanted to do so over SSH which makes me feel a bit safer.

You can enable SSH from System Preferences -> Sharing -> Check "Remote Login" and port forward that from your router if needed. If you need help port forwarding, [this is a generic solution that should work for most][lmgtfy].

Also, consider changing the default SSH port to something other that port 22 to avoid random attacks at your IP address. [Check out this serverfault question on how to do that.][serverfault]

Open an SSH tunnel to your remote ownCloud server like so:

~~~ bash

ssh -L 5900:localhost:80 user@your_host_ip

~~~
<br>
This tunnels all traffic from your remote port 80 to your local port 5900. Once you've authenticated that connection, you can go to your web browser on this computer and access your ownCloud with `http://localhost:5900/owncloud`

![](/images/20140105/4.png)

<br>
Refs: 

-	[Adding an internal directory or external hard drive to Owncloud server][external]
-	[Wordpress Options FollowSymLinks error][symlink]
-	[OS X Mountain Lion 10.8 Set Apache and PHP Web-Server][apache]
-	[Install Owncloud on a Mac mini server][macmini]
-	[ownCloud Administrators Manual][owncloud_docs]

[support]: http://doc.owncloud.org/server/5.0/admin_manual/installation/installation_macos.html
[download]: http://owncloud.org/install/
[lmgtfy]: http://lmgtfy.com/?q=how+to+port+forward
[serverfault]: http://serverfault.com/questions/18761/how-to-change-sshd-port-on-mac-os-x
[external]: http://www.ranjith.info/p/owncloud.html
[symlink]: http://stackoverflow.com/questions/9720325/wordpress-options-followsymlinks-error
[apache]: http://www.cyberciti.biz/faq/enable-apache2-2-php5-on-apple-os-x-10-8-mountain-lion/
[macmini]: http://blog.macminicolo.net/post/30393400851/install-owncloud-on-a-mac-mini-server
[owncloud_docs]: http://doc.owncloud.org/server/5.0/admin_manual/installation.html