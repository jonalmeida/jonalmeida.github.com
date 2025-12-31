---
title: "Editing YAML front matter in bulk"
date: 2025-12-28
updated: 2025-12-30T17:04:53-05:00
draft: false
taxonomies:
  tags: ["blog"]
  categories: ["TIL"]
extra:
  hide_table_of_contents: true
---

When you want to edit YAML front matter in bulk on markdown files or similar, the tool `yq` works for this with similar syntax to `jq` for JSON query/transformation.

First, try out the queries without writing them to the files:

```bash
find . -name  "*.md" -exec yq --front-matter="extract" '.taxonomies.categories[]' {} \;
```

> [!NOTE] This pipes only the extracted YAML properties output to the terminal. Keep reading below for writing it to the file.

To append to the categories with new entries:

```bash
find . -name  "*.md" -exec yq --front-matter="extract" '.taxonomies.categories[] += "archive"' {} \;
```

When we're ready to write our changes to the file, we use `--front-matter="process"` and the in-place flag `-I` (using the example above):

```bash
find . -name  "*.md" -exec yq --front-matter="process" '.taxonomies.categories[] += "archive"' -i {} \;
```



[0]: https://github.com/mikefarah/yq	"yq is a portable command-line YAML properties processor"
