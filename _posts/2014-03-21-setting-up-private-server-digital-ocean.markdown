---
layout: post
title: Setting up my private server on Digital Ocean
category: posts

---

Today I joined DigitalOcean and created my host server which they refer to as "Droplets". Within a few hours I had set-up my host server *exactly* how I wanted it faster than I would have ever imagined with the set-up process from DigitalOcean made so simple.

There's nothing to really say or explain about their set-up process. It's just easy and simple. Choose a hostname, host size, server location, base OS image and optional SSH keys if you don't want to use a password.

### Update First
I chose my base image as Ubuntu 12.04 x64 being an LTS I find it much nicer to use. First things first, I SSH'd in and `apt-get update && apt-get upgrade` to make everything was up-to-date.

### Docker
I'm learning deployment with docker so I had that installed as well. It's worth mentioning that DO has a BETA feature when creating your Droplet for pre-installing applications like Docker, Ghost or GitLab, but I prefer doing this myself so I know exactly what is installed. I followed the [Docker installation guide for Ubuntu 12.04][1], but I skipped updating the kernel since the base image was already using kernel 3.8.x.

### Private VPN
I always wanted to have access to all my boxes at all times, and DO has a nice simple guide to setting up a PPTP VPN on your server to allow connected clients to communicate with each other. You can find the article [here][2]. 

> If you to run your traffic through any one of your other clients (and they also have an SSH server running on them), I've found using sshuttle really easy for that.

> When connected via VPN you can use `sshuttle --dns -r [PPTP_IP_ADDRESS] 0/0` to have your traffic including your DNS go through the client of your choice. It's helpful if you have clients in different countries and need local web access for whatever reason.

### Sub-domain
When you create your droplet, you're given an external IP that you can use to remote in, but no one wants to remember that. Since I have my domains managed with [namecheap.com][3] I chose to manage this server as a domain through that instead of DO's own nameservers.

The blurred out bit in the image below, is where you would enter your external IP address and the sub domain is up to you.

![](/images/20140321/1.png)

### Git
This was probably the easiest bit, just install git: `apt-get install git git-core`
Everything was going to do be done as a private repo for now so it would be behind SSH and I didn't care for having an web interface on it. You can find more details on [settings up a git server correctly][4], but essentially all you need to do is:

``` bash
mkdir my-repo.git
cd my-repo.git
git --bare init
```
<br>
Clients would add the remote as:

``` bash
git remote add origin ssh://jonathan@jonalmeida.dyndns.org/location/of/my-repo.git
```
### Configuring clients
Most Linux OSes come with a PPTP client installed so setting that up is quite trivial.
I created a few SSH configurations so I can type less:

``` bash
Host atlas
    HostName atlas.somedomain.com
    User jonathan
```
<br>
As well as a few aliases in my `.bashrc` that looked something like this:

``` bash
alias atlas-connect='sshuttle --dns -vvr jonathan@atlas.somedomain.com 0/0'
```

## Conclusion
If you found any of this useful and you're going to join Digital Ocean as well, why not use [my referral link][5] instead. :)

[1]: http://docs.docker.io/en/latest/installation/ubuntulinux/
[2]: https://www.digitalocean.com/community/articles/how-to-setup-your-own-vpn-with-pptp
[3]: http://namecheap.com
[4]: http://www.git-scm.com/book/en/Git-on-the-Server-Setting-Up-the-Server
[5]: https://www.digitalocean.com/?refcode=8492838d309e