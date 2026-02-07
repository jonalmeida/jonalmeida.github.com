---
title: "Test a Firefox Android variant alongside your daily driver"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["workflow", "mozilla"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

In the Mozilla Android team, we want engineers to talk with Product and UX more and hash out ideas sooner. Prototype an idea, then discuss the feature's merits. For this, we built [TryFox](https://github.com/mozilla-mobile/TryFox/) to make it easier for everyone to get the latest version of Firefox Nightly or install a "try" build with a link to the build on our CI servers.

The downside with using a Try build is that you sometimes have to uninstall your existing version of Nightly before you can install another and that means losing app data. Typically, if you were doing this on your daily driver, you don't want to do that. A quick work around is to add a temporary patch above your stack of commits which changes the App ID suffix (and optionally the application name) so that there is no conflict.

Here is an example diff from a patch that changed an animation, so having it install alongside what we shipped let you compare them easily:


```diff
diff --git a/mobile/android/fenix/app/build.gradle b/mobile/android/fenix/app/build.gradle
index 019fdb7ab4..772cc6cc3d 100644
--- a/mobile/android/fenix/app/build.gradle
+++ b/mobile/android/fenix/app/build.gradle
@@ -127,7 +127,7 @@
         debug {
             shrinkResources = false
             minifyEnabled = false
-            applicationIdSuffix ".fenix.debug"
+            applicationIdSuffix ".fenix.debug_animator"
             resValue "bool", "IS_DEBUG", "true"
             pseudoLocalesEnabled = true
         }
diff --git a/mobile/android/fenix/app/src/main/res/values/static_strings.xml b/mobile/android/fenix/app/src/main/res/values/static_strings.xml
index 4f6703eb35..1a57988477 100644
--- a/mobile/android/fenix/app/src/main/res/values/static_strings.xml
+++ b/mobile/android/fenix/app/src/main/res/values/static_strings.xml
@@ -4,7 +4,7 @@
    - file, You can obtain one at http://mozilla.org/MPL/2.0/. -->
 <resources xmlns:moz="http://schemas.android.com/apk/res-auto" xmlns:tools="http://schemas.android.com/tools">
     <!-- Name of the application -->
-    <string name="app_name" translatable="false">Firefox Fenix</string>
+    <string name="app_name" translatable="false">Firefox Fenix (animator)</string>
     <string name="firefox" translatable="false">Firefox</string>

     <!-- Preference for developers -->
```

In the future, we can add `mach try` support to do this automatically for any push.
