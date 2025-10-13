---
layout: post
title: Pushing to multiple existing git repositories
categories: posts
aliases: ['/posts/2013/04/09/pushing-to-multiple-existing-git-repositories']
taxonomies:
  tags: ['workflow']
---

I've come across this situation where I start a project and push it to a personal git server, but eventually change my mind and decide to push those changes to another git server like Github or the university servers.

To push those existing changes, first make sure that you're local copy of your repository is up-to-date with a simple `git pull`. You want to edit the existing `.git/config` file that originally looks like this:

~~~ ini
[core]
  repositoryformatversion = 0
  filemode = true
  bare = false
  logallrefupdates = true
[remote "origin"]
  url = git@github.com:User/MyProject.git
  fetch = +refs/heads/*:refs/remotes/origin/*
~~~
<br>

By adding another remote, like so: `git remote add foobar git_address_here`. You should notice your git config file will now like this:

~~~ ini
[core]
  repositoryformatversion = 0
  filemode = true
  bare = false
  logallrefupdates = true
[remote "origin"]
  url = git@github.com:User/MyProject.git
  fetch = +refs/heads/*:refs/remotes/origin/*

[remote "foobar"]
  url = ssh://my_server/~/Repo/UberWriter.git
  fetch = +refs/heads/*:refs/remotes/foobar/*
~~~


Now you have two remote repositories setup in your configuration. Simply run a git push with the new remote and that should push all the changes from your local repo, to your new remote: `git push foobar master`

If you want to take it a further step and push to both remotes at the same time (nothing wrong with a backup of a backup), manually edit your `.git/config` file to add both your repositories as a separate remote, but DO NOT add a 'fetch' variable in there, like so:

~~~ ini
[remote "all"]
  url = git@github.com:User/MyProject.git
  url = ssh://my_server/~/Repo/UberWriter.git
~~~

Now before you push to both the repositories at the same time, make sure both of them are at the same HEAD otherwise it'll not work:

~~~ ini
git push all
~~~

This should be enough to push to the default branch for both of the two repositories.
