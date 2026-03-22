---
title: "Use |mach try --no-push| for a configuration dry run"
draft: false
#updated: 2026-01-19T16:08:32-05:00
taxonomies:
  tags: ["workflow", "mozilla"]
  categories: ["til"]
extra:
  hide_table_of_contents: true
---

I wanted to see what the generated try configuration would be for a new preset I made and did this by submitting real try pushes (with `empty` so they don't execute resources). What I was looking for was "dry run" in the help files, but I recently discovered it to be `--no-push`.

```bash
$ jj try-push --preset fenix --no-push # 'fenix' as an example preset
Artifact builds enabled, pass --no-artifact to disable
Commit message:
Fuzzy (preset: fenix) query='build-apk-fenix-debug&query='signing-apk-fenix-debug&query='build-apk-fenix-android-test-debug&query='signing-apk-fenix-android-test-debug&query='test-apk-fenix-debug&query='ui-test-apk-fenix-arm-debug&query=^source-test 'fenix&query='generate-baseline-profile-firebase-fenix

mach try command: `./mach try --preset fenix --no-push`

Pushed via `mach try fuzzy`
Calculated try_task_config.json:
{
    "parameters": {
        "optimize_target_tasks": false,
        "try_task_config": {
            "disable-pgo": true,
            "env": {
                "TRY_SELECTOR": "fuzzy"
            },
            "tasks": [
                "build-apk-fenix-android-test-debug",
                "build-apk-fenix-debug",
                "generate-baseline-profile-firebase-fenix",
                "source-test-android-detekt-detekt-fenix",
                "source-test-android-l10n-lint-l10n-lint-fenix",
                "source-test-android-lint-fenix",
                "source-test-buildconfig-buildconfig-fenix",
                "source-test-ktlint-fenix",
                "source-test-mozlint-android-fenix",
                "test-apk-fenix-debug",
                "ui-test-apk-fenix-arm-debug",
                "ui-test-apk-fenix-arm-debug-smoke"
            ],
            "use-artifact-builds": true
        }
    },
    "version": 2
}
```

Here, `jj try-push` is my quick alias around `./mach try` for personal simplicity with my workflow.
