---
layout: post
title: Setting up my private server on DigitalOcean
categories: posts
tags: [Archived]

---

Today I joined DigitalOcean and created my host server which they refer to as "Droplets". Within a few hours I had set-up my host server *exactly* how I wanted it faster than I would have ever imagined with the set-up process from DigitalOcean that made so simple.

There's nothing to really say or explain about their set-up process. It's just easy and simple - choose a host name, host size, server location, base OS image and optional SSH keys if you don't want to use a password.

-----

> **EDIT:**
> I decided to install Gitlab after all, so I manually installed gitlab to my server but it seemed to severly slow it down. Instead, I created a new Droplet with the [One-Click Install Image for Gitlab][7] (for some reason this version is less memory intensive), and then moved all my configuration/setup to the new Droplet.

> Also I moved the gitlab instance from running at '/' to '/gitlab' instead.
> With v6.6 it was pretty easy with the documentation within the configuration. You basically have to make four changes:

> 1. In your application.rb file: `config.relative_url_root = "/gitlab"`
> 2. In your gitlab.yml file: `relative_url_root: /gitlab`
> 3. In your unicorn.rb: `ENV['RAILS_RELATIVE_URL_ROOT'] = "/gitlab"`
> 4. In ../gitlab-shell/config.yml: `gitlab_url: "http://127.0.0.1/gitlab"`
> 5. In lib/support/nginx/gitlab : do not use asset gzipping, remove block starting with "location ~ ^/(assets)/"

-----

### Update First
I chose my base image as Ubuntu 12.04 x64 being an LTS, I find it much nicer to use. First things first, I SSH'd in and `apt-get update && apt-get upgrade` to make sure everything was up-to-date.

### Docker
I'm learning more about deployment using docker so I had that installed as well. It's worth mentioning that DO has a BETA feature when creating your Droplet with pre-installing applications like Docker, Ghost or GitLab. However, I prefer doing this myself so I know exactly what is installed. I followed the [Docker installation guide for Ubuntu 12.04][1], but I skipped updating the kernel since the base image was already using kernel 3.8.x.

### Private VPN
I always wanted to have access to all my boxes at all times, and DO has a nice simple guide to setting up a PPTP VPN on your server to allow connected clients to communicate with each other. You can find the article [here][2]. 

> If you want to run your traffic through any one of your other clients (and they also have an SSH server running on them), I've found using sshuttle really easy for that.

> When connected via VPN you can use `sshuttle --dns -r [PPTP_IP_ADDRESS] 0/0` to have your traffic including your DNS go through the client of your choice. It's helpful if you have clients in different countries and need local web access for whatever reason.

### Sub-domain
When you create your droplet, you're given an external IP that you can use to remote in, but no one wants to remember that. Since I have my domains managed with [namecheap.com][3] I chose to manage this server as a domain through that instead of DO's own nameservers.

The blurred out bit in the image below, is where you would enter your external IP address and the sub domain is up to you.

![](/images/20140321/1.png)

### Git
This was probably the easiest bit, just install git: `apt-get install git git-core`.
Everything was going to do be done as a private repo for now so it would be behind SSH and I didn't care for having a web interface for it. You can find more details on [settings up a git server correctly][4], but essentially all you need to do is:

~~~ bash

mkdir my-repo.git
cd my-repo.git
git --bare init

~~~
<br>
Clients would add the remote as:

~~~ bash

git remote add origin ssh://jonathan@atlas.somedomain.com/location/of/my-repo.git

~~~

### Configuring clients
Most Linux OSes come with a PPTP client installed so setting that up is quite trivial.
I created a few SSH configurations so I can type less:

~~~ bash

Host atlas
    HostName atlas.somedomain.com
    User jonathan

~~~
<br>
As well as a few aliases in my `.bashrc` that looked something like this:

~~~ bash

alias atlas-connect='sshuttle --dns -vvr jonathan@atlas.somedomain.com 0/0'

~~~

### Swap File
If you're using the 512MB RAM configuration, it's also wise to setup a swap file since you will inevitably run into low memory issues *very* soon. DO have yet another very [handy tutorial on how to do exactly that][6].

## Conclusion
If you found any of this useful and you're going to join DigitalOcean as well, why not use [my referral link][5] instead. :)

[1]: http://docs.docker.io/en/latest/installation/ubuntulinux/
[2]: https://www.digitalocean.com/community/articles/how-to-setup-your-own-vpn-with-pptp
[3]: http://namecheap.com
[4]: http://www.git-scm.com/book/en/Git-on-the-Server-Setting-Up-the-Server
[5]: https://www.digitalocean.com/?refcode=8492838d309e
[6]: https://www.digitalocean.com/community/articles/how-to-add-swap-on-ubuntu-12-04
[7]: https://www.digitalocean.com/community/articles/how-to-use-the-gitlab-one-click-install-image-to-manage-git-repositories