---
layout: post
title: Different ways to implement flags in bash
categories: posts
aliases: ['/posts/2013/05/26/different-ways-to-implement-flags-in-bash']
---

I had to write a couple of shell script which required me to execute a part of the script by passing a flag. Should be easy enough?

Writing the part for capturing flags wasn't that hard, but there were many options available so it took a while to ponder on what I needed and while purpose suit me. I've seen implementations where people use simple if statements for dot files as so:

~~~ bash
#!/bin/bash
if [ "$1" == "quack" ]; then
  echo QUACK!
fi
~~~

Sure, that works, but not exactly for my needs since I have multiple flags to handle. Which lead me to getopts. Using getopts was a bit fancy, but when you realize how easy it is to implement you'll learn to love it. I'm not going to repeat what Ricardo Salveti has done quite well in his blog here, but after reading it, this was my implementation:

~~~ bash
#!/bin/bash
while getopts "bf:" OPTION
do
  case $OPTION in
    b)
      echo "You set flag -b"
      exit
      ;;
    f)
      echo "The value of -f is $OPTARG"
      MYOPTF=$OPTARG
      echo $MYOPTF
      exit
      ;;
    \?)
      echo "Used for the help menu"
      exit
      ;;
  esac
done
~~~

In a nutshell, it's a while statement with cases. The "bf:" says that only a flag '-b' needs to be entered by the user, '-f' has a semicolon after it to indicate that it's expecting a value with the flag, similar to writing `foo.sh -f my_value_here`.

The beauty of getopts is that it can handle the same flag multiple times. If you would do that with the current code about it wouldn't spit out any errors, but it wouldn't work as expected. Lets say you wanted to use the '-f' flag twice. The value of MYOPTF would be _the value of last -f value used and no other_. This can be solved with a small modification:

~~~ bash
#!/bin/bash
while getopts "f:" OPTION
do
  case $OPTION in
    f)
      MYOPTF="$MYOPTF $OPTARG"
      echo MYOPTF
      ;;
  esac
done
~~~

That should work fine since you have a list of all the values, you can easily iterate through it with a for loop.

The disadvantage (as far as my use case is concerned) with getopts is that it only accepts single character flags so you couldn't use flags like `--help` which the gnu styled arguments and is a bit unfortunate.

I finally decided to use a hybrid of all the information I put together since I ran into the case where I needed to accept either option '-h' or `--help`:

~~~ bash
#!/bin/bash
while [ ! $# -eq 0 ]
do
  case "$1" in
    --help | -h)
      helpmenu
      exit
      ;;
    --take-over-world | -t)
      secretopt
      exit
      ;;
  esac
  shift
done
~~~

You would have noticed I threw in a bunch of stuff that I didn't mention previously, and that's sort of the assumption I made.
What I've essentially done in `while [ ! $# -eq 0 ]` is I've said, while the number of arguments are not zero, do so and so.
The $1 is the first argument that's passed the script at execution, to avoid having to write cases for $2, $3, etc. I "shift" the argument off my list once I'm done processing it through my case statements, and then repeat while arguments exist.
