# Reference directory

Start with the [reference index](../docs/REFERENCES.md) and [reuse notes](../docs/upstream-reuse.md). `sources.lock.json` pins source commits, paper versions, file sizes and SHA-256 hashes; `references.bib` provides paper citations.

```bash
python scripts/prepare_references.py
python scripts/prepare_references.py --check
```

By default, the tool prepares the core source files and examples. Add `--papers` to download paper PDFs or `--assets` to download the initial character reference images. Downloads require network access and are stored in ignored directories. Once cached files pass verification, they can be read offline.
