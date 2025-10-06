---
layout: post
title: How I manage my github notifications with Gmail
categories: posts
---

A lot of [Mozilla mobile][3] product development is now hosted on Github, which is what many of our contributors prefer as a platform too. This leads to a lot of noise from Github's notification system and I've had some troubles managing it over the years.

As a follow-up to [how you can manage bugmail with gmail][0], I found a similar way to manage my most important Github notifications via Gmail:

![][1]

You can apply the same filters with the rules below:

```

Matches: from:(notifications@github.com)
Do this: Skip Inbox, Apply label "GitHub", Categorize as Forums

Matches: to:(author@noreply.github.com)
Do this: Apply label "GitHub/Author", Mark it as important

Matches: cc:comment@noreply.github.com
Do this: Skip Inbox, Apply label "GitHub/Comments"

Matches: to:(mention@noreply.github.com)
Do this: Skip Inbox, Apply label "GitHub/Mentions"

Matches: to:(review_requested@noreply.github.com) "requested your review"
Do this: Apply label "GitHub/Review Requested", Mark it as important

Matches: to:(review_requested@noreply.github.com)
Do this: Apply label "GitHub/Reviews"

```
<br>

The filters above are sorted in the same order as the screenshot if you'd like to only use a select few.

If you're feeling ambitious, you can [download the filters][2] in the appropriate XML format for Gmail so that you can import them for your account. This is probably not advisable because I'm someone on the internet that you probably do not know. :)

[0]: https://blog.margaretleibovic.com/2012/09/21/how-i-manage-my-bugmail-with-gmail.html
[1]: /images/20211014/gmail-sidebar.png
[2]: /images/20211014/mailFilters.xml
[3]: https://github.com/mozilla-mobile/
