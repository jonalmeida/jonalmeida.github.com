---
title: "Regenerate the BuildConfig file without assembling the whole module"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["workflow", "mozilla"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

We have tokens that are added to official builds when a CI server is building the production-ready application. These tokens are added to the `BuildConfig.java` by using the `[buildConfigField`][1] function in a [`build.gradle`][0].

While testing, you want to quickly regenerate _just_ this file to see changes occur with a new value. Instead of using the more expensive `assembleDebug` task for your debug variant, you can use `generateDebugBuildConfig`.

In the Firefox monorepo world for the Fenix module, the fully-qualified task name would look like this:

```
./mach gradle :fenix:generateDebugBuildConfig
```

[0]: https://searchfox.org/firefox-main/rev/25d7109bf565c299435dec3dd2b9e79a1ce7c15d/mobile/android/android-components/components/concept/accelerometer/build.gradle#12
[1]: https://developer.android.com/reference/tools/gradle-api/7.2/com/android/build/api/variant/BuildConfigField
