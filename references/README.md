# 参考目录

先阅读 [资料索引](../docs/REFERENCES.md) 和 [复用说明](../docs/upstream-reuse.md)。`sources.lock.json` 固定源码提交、论文版本、逐文件大小和 SHA-256；`references.bib` 提供论文引用。

```bash
python scripts/prepare_references.py
python scripts/prepare_references.py --check
```

默认准备核心源码与样例；添加 `--papers` 下载论文 PDF，添加 `--assets` 下载初始角色参考图。下载内容保存在忽略目录，需联网一次。已缓存文件通过验证后可离线阅读。
