---
layout: post
title: Cleaning up a messy master branch
category: posts
tags: [Archived]

---
<br>
Note: This is for the foolish and lazy side of you

Twice I've come across a situation where I've messed up local master branch before I merge my topic branch. I've pushed commits to my local master that are now lost in the abyss so when I pull down the latest changes to the master branch I have to do a merge commit. Let's fix that with a bit of frustration..

Create a orphan branch with any branch name (we'll rename it later):

~~~ bash

git checkout --orphan any_branch_name

~~~
<br>

Pull the lastest changes:

~~~ bash

git pull origin master

~~~
<br>

Rename the branch back to master if you fancy it:

~~~

git branch -m any_branch_name master

~~~
<br>

If you're working on a topic branch, that you've previously created over your old master, you should be able to rebase it with your new branch, before you push it your remote:

~~~ bash

git checkout topic_branch
git rebase master
git checkout master
git merge topic_branch
git push origin master

~~~
<br>

A shorter way (but still somewhat untidy) to do this would be to cherry-pick your change(s) from your topic branch to your newly created local master and then push them. While this works just a well. There are changes you turn into a walking-talking-moron and screw up again if those changes aren't merged with your remote:

~~~ bash

git checkout master
git cherry-pick SHA_VALUE
git push origin master

~~~
<br>
_For the not-so-foolish..._<br>
How about a third option? I prefer this one to most though since it's the only way you _should_ be doing it.
Let's say you were working on a commit on your topic branch for a while, and your remote master has been updated a fair bit since then.
First, fetch the latest changes from upstream, rebase your topic branch to your remote's master and then push it:

~~~ bash

git fetch
git rebase origin/master
git push origin master

~~~
<br>
This way, you get your changes pushed to the top of the tree based of the remote's master (which should be the most up-to-date version you want). You don't need to maintain your local master, because hey, why the hell should you? AND.. you should be able to push to the remote repo without any errors.