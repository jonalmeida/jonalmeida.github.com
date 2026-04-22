---
title: "Gmail filters based on X-Phabricator-Stamps header"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["workflow", "mozilla"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

I want Phabricator emails to have a Gmail label so I can know which patches had me as a reviewer that then had follow-up comments from other folks.

This is useful for me when I review a patch and then I need to respond back to discussions in a more timely manner in comment threads that I've created.

It's difficult to do this today similar to [Bugzilla Gmail filters](http://blog.margaretleibovic.com/post/32008790345/how-i-manage-my-bugmail-with-gmail) because there are fewer identifiers that the more simplistic Gmail filter parameters can help with.

Today I learnt that there is an `X-Phabricator-Stamps` header in those Phabricator emails that let's you identify you as a the reviewer in a patch. So using that information, I wrote the [Google script](https://script.google.com/) below to run every minute and avoid re-processing the same email twice.

A couple variables were added to the top and some console.logs are sprinkled around for my own debugging.

<details>

<summary>Code</summary>

```js
var REVIEWER = "jonalmeida";
var LABEL_NAME = "Phabricator/Comments";
var BODY_MATCH = "commented on this revision.";
var SENDER = "phabricator@mozilla.com";

/**
 * Run once manually to install the per-minute trigger.
 */
function install() {
  uninstall();
  ScriptApp.newTrigger('processInbox')
  .timeBased()
  .everyMinutes(1)
  .create();
}

/**
 * Run once manually to remove the trigger.
 */
function uninstall() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    ScriptApp.deleteTrigger(t);
  });
  PropertiesService.getScriptProperties().deleteProperty('lastRun');
}

/**
 * Every run, we try to avoid processing the same email twice because
 * there is no API trigger to run a script on every new email received.
 */
function processInbox() {
  var props = PropertiesService.getScriptProperties();
  var lastRun = parseInt(props.getProperty('lastRun') || '0');
  var now = Math.floor(Date.now() / 1000);

  // On first run, look back 2 minutes
  if (lastRun === 0) {
    lastRun = now - 120;
  }

  var label = GmailApp.getUserLabelByName(LABEL_NAME);
  if (!label) {
    label = GmailApp.createLabel(LABEL_NAME);
  }

  console.log("last run: " + lastRun);
  var threads = GmailApp.search("from:" + SENDER + " after:" + lastRun);
  console.log("threads to process: " + threads.length);
  for (var i = 0; i < threads.length; i++) {
    var thread = threads[i];
    var messages = thread.getMessages();
    console.log("messages to process: " + messages.length);
    for (var j = 0; j < messages.length; j++) {
      if (hasReviewerStamp(messages[j])) {
        thread.addLabel(label);
        console.log(thread.getFirstMessageSubject());
        break;
      }
    }
  }

  props.setProperty('lastRun', String(now));
}

function hasReviewerStamp(message) {
  var raw = message.getRawContent();
  var match = raw.match(/^X-Phabricator-Stamps:\s*(.+)$/m);
  if (!match) {
    return false;
  }

  var stamps = match[1].trim().split(/\s+/);
  return (stamps.indexOf("reviewer(@" + REVIEWER + ")") > -1) && raw.indexOf(BODY_MATCH) > -1;
}

/**
 * For debugging - see the list of labels you can search which
 * differs from what is used in the Gmail UI filter.
 */
function listAllLabels() {
  console.log("All labels");
  var labels = GmailApp.getUserLabels();
  for (var i = 0; i < labels.length; i++) {
    console.log(labels[i].getName());
  }
}
```

</details>
