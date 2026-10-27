# 情绪评测脚本

这些脚本用来复现 [情绪评测研究记录](../../docs/studies/emotion-evaluation-20261027/README.md) 里的 VEMOCLAP 单路消融、特征互换、变暗对照和 VBench 画面质量评测。仓库不包含视频、模型权重和上游代码，也不写死任何本机路径，目录通过环境变量给出：

| 环境变量 | 内容 |
|---|---|
| `VEMOCLAP_UPSTREAM` | 上游 VEMOCLAP 代码和权重目录，获取与固定版本见 [docs/vemoclap.md](../../docs/vemoclap.md) |
| `MOODCUT_EVAL_WORK` | 工作目录：`videos/<video_id>.mp4`（例如 `videos/s09/baseline.mp4`）、各视频的结果目录、`vbench/`、`dark/` |
| `MOODCUT_VEMOCLAP_CACHE` | VEMOCLAP 的 CLIP 等缓存目录，见 [docs/vemoclap.md](../../docs/vemoclap.md) |

视频文件必须与 `video_manifest.json` 里的 `sha256` 一致，`run_vemoclap_batch.py` 会在不一致时跳过并提示。

| 脚本 | 作用 |
|---|---|
| `vemoclap_ablate.py` | 保存五路特征（asr_sentiment、beats、clip、face_emotion、ocr_sentiment），逐路置零或只保留一路后重新分类，写 `ablation.json` 和 `features.pt` |
| `run_vemoclap_batch.py` | 按清单对所有视频运行上一个脚本，相同文件只跑一次 |
| `collect_results.py` | 把各视频结果和 VBench 分数收集成仓库里提交的 `results/*.json` |
| `swap_conditions.py`、`audio_tail_swap.py` | 同一故事三个条件之间互换某一路特征、互换音频尾段，检验结果是否跟着音频走 |
| `film_clip_combos.py` | 对真人电影片段只保留或互换若干路特征 |
| `feature_swap_fear.py` | 恐惧专项：用真实恐怖片段的特征替换和反向替换，检验哪一路决定 fear |
| `darken_and_eval.py` | 用 ffmpeg 只降亮度（音频不变）后重新评测 |
| `audio_check.py`、`audio_probe.py`、`asr_all.py`、`face_probe.py` | 音轨响度和 BEATs 标签、Whisper 转写、人脸检测输出，用来排查特征 |
| `dim_audio.py`、`text_go.py` | 语音唤醒度/支配度/情感价模型和 GoEmotions 文本模型，探索性代理 |
| `analyze_mapping.py` | 只读已提交结果，检验六类情绪概率能否分开亲密、敌对、紧张（不需要任何模型） |
| `make_vbench_manifest.py`、`run_vbench_batch.sh` | 生成 VBench imaging_quality 清单并运行，环境和固定版本见 [docs/vbench.md](../../docs/vbench.md) |

`swap_conditions.py`、`audio_tail_swap.py` 和 `film_clip_combos.py` 读取 `<MOODCUT_EVAL_WORK>/results2` 或 `results3` 下的 `features.pt`，这些目录名与 `video_manifest.json` 的 `result_dir` 一致；真人电影片段的版权状态未确认，片段不随仓库提供。

不需要任何模型就能运行的部分：

```bash
python scripts/emotion_eval/analyze_mapping.py
python -m unittest discover -s tests -p "test_emotion_eval_results.py"
```
