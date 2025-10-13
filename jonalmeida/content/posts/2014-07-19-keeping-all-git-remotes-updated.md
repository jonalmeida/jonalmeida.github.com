---
layout: post
title: How to keep all your git remotes up-to-date
categories: posts
aliases: ['/posts/2014/07/19/keeping-all-git-remotes-updated']
---

You always want your copy of remote in your local repository up-to-date. Having a bunch of git repos doesn't help because now you have to check them all (20+ amiright?!). A small portion of my busy-work goes into fetching and rebasing before I start to work on any project.

So I wrote a small bash script which includes stuff that [I learned about bash flags previous][bash-flag], and merged it into one script that does something fairly neat:

- It goes through each git repository in `~/git` directory (you can change this to another directory with the `-d` flag)
- `git fetch`
- Attempts to do a `git rebase origin/{current_branch}`
- If it fails, it'll try a `git stash` to remove any files that are still a work-in-progress
- Attempts a git rebase once again
- Executes `git stash pop` regardless if it was successful or not

Also note, that you can change your remote from `origin` to something else with the `-r` flag. Although, you should note that this will the remote used in all git repos.

You can find the code in the snippet below, but the most up-to-date version can always be found [on GitHub][github-link].
<br>

~~~ bash

#!/bin/bash

# Default git directory
git_dir=~/git
# Default remote
git_remote="origin"

function helpmenu {
    echo "USAGE EXAMPLE:"
    echo "    fetch-all.sh ~/directory_of_git_repos origin"
}

function setDir {
    if [[ $checkDir != "" ]]; then
        # Path is passed as first argument
        ls $checkDir 1>&2
        if [[ $? != 0 ]]; then
            # Path isn't valid
            echo "Cannot access $1: No such directory"
            exit
        fi
        git_dir=$checkDir
    fi
}

function setRemote {
    if [[ $checkRemote != "" ]]; then
        # Second argument is not empty
        # (Should contain a branch)
        git_remote=$checkRemote
    fi
}

while getopts "hd:r:" OPTION
do
    case $OPTION in
        h)
            helpmenu
            exit
            ;;
        d)
            checkDir=$OPTARG
            setDir
            # break
            ;;
        r)
            checkRemote=$OPTARG
            setRemote
            # break
            ;;
        \?)
            helpmenu
            exit
            ;;
    esac
done

echo "Changing directory to $git_dir"
cd $git_dir

for dir in */; do
    echo "=========================================="
    echo $dir
    cd $dir
    echo "---"
    echo "git fetch"
    git fetch
    echo "---"
    echo "git rev-parse --abbrev-ref HEAD"
    current_branch=`git rev-parse --abbrev-ref HEAD`
    echo "current_branch = $current_branch"
    echo "---"
    echo "git rebase $git_remote/$current_branch"
    git rebase $git_remote/$current_branch
    if [[ $? != 0 ]]; then
        echo "---"
        echo "git stash"
        git stash
        echo "---"
        echo "git rebase $git_remote/$current_branch"
        git rebase $git_remote/$current_branch
        second_attempt=$?
        echo "---"
        echo "git stash pop"
        git stash pop
    fi
    if [[ second_attempt == 1 ]]; then
        echo "Your repo ($dir.git) has problems.."
    fi
    echo "---"
    echo "cd .."
    cd ..
done;

~~~

<br>
Refs: 

-   [Git Status From Outside of the Working Directory][git-working-dir]

[git-working-dir]: http://www.bubblefoundry.com/blog/2011/02/git-status-from-outside-of-the-working-directory/
[bash-flag]: /posts/2013/05/26/different-ways-to-implement-flags-in-bash/
[github-link]: https://github.com/jonalmeida/snippets/blob/master/git/fetch-all.sh