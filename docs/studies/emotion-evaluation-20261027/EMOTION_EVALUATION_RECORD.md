# 情绪评测流程与探索记录

作者：范旭阳（GitHub：fanx9905-blip）　·　2026-10-25 至 2026-10-27

状态：**开发期探索性结果**。每个条件只有一个视频，没有人工盲评，不能据此宣称 MoodCut 更强或更弱。本目录只含脚本、清单、数值结果和文字记录，不含视频、模型权重和个人评分信息。

## 分支简介 / Branch description

**中文**　本分支 `feat/issue-9-emotion-evaluation-pipeline` 把 2026-10-25 至 10-27 做的情绪评测整理成可复现的流程，并记录评测规则和评测集的迭代。具体改动：

1. **新增研究记录**（本目录）：规则怎么改的（V0→V1→V2→V3 均为历史方案，现行做法是直接评测六种情绪）、消融和对照实验步骤、逐视频结果、人工评分方案草案。
2. **新增评测脚本** `scripts/emotion_eval/`：VEMOCLAP 单路消融、特征互换、变暗对照、VBench 批处理和只读结果的分析；路径全部来自环境变量。
3. **带入 VEMOCLAP 适配器**：`src/moodcut/vemoclap*.py`、`configs/vemoclap-*`、`docs/vemoclap.md`、许可证和测试，脚本依赖它们。
4. **修改项目 README**（中英文）：`Current progress` 增加评测集迭代，`Quick start` 之后新增 `Using the evaluation sets`，文档导航增加本记录。

**English**　This branch, `feat/issue-9-emotion-evaluation-pipeline`, turns the evaluation done between 2026-10-25 and 10-27 into a reproducible pipeline and records how the scoring rules and evaluation sets evolved. What changed:

1. **Study record** (this folder): how the rules changed (V0→V1→V2→V3 are all historical; the current approach scores the six emotions directly), the ablation and control experiments, per-video results and a draft human-rating protocol.
2. **Evaluation scripts** in `scripts/emotion_eval/`: per-modality VEMOCLAP ablation, feature swaps, brightness control, VBench batch helpers and an analysis that runs on the committed results; all paths come from environment variables.
3. **VEMOCLAP adapter**: `src/moodcut/vemoclap*.py`, `configs/vemoclap-*`, `docs/vemoclap.md`, the license and tests that the scripts depend on.
4. **Project README** (English and Chinese): `Current progress` gains the evaluation-set iteration, `Quick start` is followed by `Using the evaluation sets`, and the documentation table links this record.

### 评测集在哪里 / Where each evaluation set lives

| 评测集 Set | 场景输入 Scene inputs | 索引 Index | 分配配置 Config | 结果 Results |
|---|---|---|---|---|
| S01–S06（三种氛围，历史）| `docs/studies/six-story-clear-emotions-20261024/inputs/s01_…`–`s06_…` | `inputs/index.json` | — | `results/vemoclap_all.json` 中 `label_system = atmosphere3` 的 29 条记录 |
| S07–S12（六种情绪，现行）| `inputs/s07_…`–`s12_…` | `inputs/basic-emotions-index.json` | `configs/basic-emotions-experiment.json` | `vemoclap_all.json` 中 `label_system = emotion6`；本文第 6 节 |
| S13–S18（审查挑战）| `inputs/s13_…`–`s18_…`（含 `draft-dialogue.json`）| `inputs/basic-emotion-challenge-index.json` | `configs/basic-emotions-challenge-experiment.json` | 目前只评测了 S15（`vemoclap_all.json`、第 6 节）|
| 真人电影片段（校准，历史）| 不随仓库提供 | — | — | `results/film_clips_vemoclap.json` |

### 实验分析结果在哪里（给做 PPT 的同学）/ Where to find the analysis results

| 要找的内容 What | 位置 Where |
|---|---|
| 评测规则怎么改的 Rule iteration | 本文第 4 节 |
| 六种情绪逐视频概率表 Six-emotion table | 本文第 6 节；原始数据 `results/vemoclap_all.json` |
| 消融步骤和结论 Ablation steps | 本文第 5 节；每条视频的逐路去掉/保留结果在 `results/vemoclap_all.json` |
| 恐惧专项特征交换 Fear feature swap | `results/fear_feature_swap_s09_s15.txt`，结论见第 5 节第 7 条 |
| 变暗对照 Brightness control | `results/dark_experiment.json`，表格见第 5 节第 8 条 |
| VBench 画面质量 VBench scores | `results/vbench_scores.json`，结论见第 7 节 |
| 视频清单与哈希 Video manifest | `video_manifest.json` |
| 人工评分方案、S09 第二版草稿 Protocol drafts | `protocols/` |
| 复现脚本 Scripts | `../../../scripts/emotion_eval/README.md` |

## 1. 要回答的问题

MoodCut 生成的两人对话视频（三个条件：baseline＝共同初稿、generic_review＝通用审查、moodcut＝情绪专项审查，只有对白不同），是否更强地传达了目标情绪或氛围？本分支用两个自动工具做辅助评测，人工盲评仍是主要证据（方案草案见 `protocols/`，尚未执行）：

- **VEMOCLAP**：视频情绪分类器，同时看声音、画面、人脸、台词文字，输出 anger、disgust、fear、joy、sadness、surprise 六类概率。
- **VBench imaging_quality**：每帧 MUSIQ 分数的平均值除以 100，只评画面质量，不评情绪。

## 2. 一句话结论

1. 把六类情绪合并成“亲密、敌对、紧张”三种氛围不可靠：亲密与有冲突的氛围能分开，紧张和敌对在情绪概率上重叠。所以后期改为**直接评测六种情绪**（S07–S12、S15）。
2. 六种情绪里，愤怒和厌恶可用，悲伤只有一个故事支持，喜悦和惊讶分不开，恐惧识别不出来。
3. 恐惧识别不出来的主要原因是**视觉特征**：模型把这些动画画面读成惊讶、愤怒或悲伤；只有画面被压得很暗时 fear 才升高，而这不等于视频传达了恐惧。
4. VBench 看不出 moodcut 让画面质量变好或变差（12 组：平均差 +0.0089，95% 自助区间 [−0.0053, +0.0238]，5 组更高、7 组更低）。
5. 自动结果主要由音频决定，且容易被背景音乐翻转。

## 3. 时间线

日期依据结果文件的时间戳；10 月 25 日 20 点之前的准备工作没有保留时间记录，合并在 10 月 25 日。

- **10 月 25 日**：接手此前未完成的 VEMOCLAP 评测任务；排查 anger 被判成 surprise 的倾向；挑选并核对两人对话的真人电影片段做校准；对项目视频（S06 十五秒、Anna/Elsa 等）做 VEMOCLAP 并第一次做单路消融，发现结果主要由音频决定；事先冻结规则 V2 并用新片段校验；评测 S01 v4。
- **10 月 26 日**：评测 S01 十五秒；探索语音唤醒度/支配度/情感价模型和 GoEmotions 文本代理，均不理想；评测 S04（紧张）；搭建固定版本的 VBench 环境，评测 S03、S05 英文新视频和所有已有项目视频；写人工盲评方案增补草案；汇总成共享页面。
- **10 月 27 日**：补测网站上的 S06 视频；分析紧张为什么被判成敌对，提出 V3（冲突闸门）；倒推能否由六类概率区分三种氛围；改为直接评测六种情绪，评测 S07–S12 和 S15；对恐惧视频做逐路消融、特征互换和变暗对照；起草 S09 探索性第二版；整理本分支。

## 4. 评测规则是怎么改的

| 版本 | 规则 | 为什么改 | 结果 | 状态 |
|---|---|---|---|---|
| V0 | 敌对＝anger，紧张＝fear，亲密＝joy | 名字最接近 | 12 个预试视频对 7 个；亲密 5 个全错：joy 几乎为 0，被读成 sadness 或 surprise | 放弃 |
| V1 | 在 V0 上，surprise ≥ 50% 弃判 | surprise 含义不清 | 被指出不合理：目标就是确定对应关系，不应丢掉这类视频 | 被 V2 取代 |
| V2 | 敌对＝anger＋disgust，紧张＝fear，亲密＝joy＋sadness＋surprise，取得分最高的一组，不弃判 | 上游情绪价表里 surprise 为正；预试里 surprise 只出现在亲密视频；规则在看校验结果之前冻结（`protocols/frozen_rule_v2.json`） | 29 条项目视频记录对 20 条：亲密 9/9，敌对 11/12，紧张 0/8；真人电影校验未达标（标准 6 中至少 5） | 实现于 `src/moodcut/vemoclap_atmosphere.py`，对紧张无效 |
| V3（提议） | 只判有没有冲突：anger＋disgust＋fear ≥ 50% 为冲突类，否则为亲密；紧张和敌对交给人工 | 紧张视频冲突量 77.0–98.8%，亲密视频 0.2–9.6% | 29 条里 28 条（看过数据后设计，未验证） | 未冻结 |
| 六种情绪 | 不再对应氛围，直接看六类概率 | 倒推发现紧张与敌对不可分（见下） | 见第 6 节 | 现行方向 |

**倒推紧张与敌对能否分开**（`scripts/emotion_eval/analyze_mapping.py`，只读已提交结果）：在 19 条冲突类视频里，anger 的 AUC 只有 0.31（两类完全重叠），fear 为 0.08（紧张的 fear 平均只有 6.5%），只有 disgust 的 AUC 达 0.97，但这是“充分不必要”：敌对里有三条 disgust 很低、anger 高达 96–99%，与紧张无法区分。“冲突闸门＋disgust ≥ 5%”留一组验证 24/29，是在看过数据后选的阈值，且紧张只有 S03、S04 两个故事，不能当规则。

## 5. 消融和对照实验步骤

所有实验都不重新训练模型，只对 VEMOCLAP 的五路特征（asr_sentiment、beats、clip、face_emotion、ocr_sentiment）做操作后再过分类器。

1. **单路消融**（`vemoclap_ablate.py`）：对每个视频保存五路特征，分别做“去掉一路（置零）”“只保留一路”“全部置零”。注意缺失特征补零会偏向 fear：全零输入得到 fear 91.8%，所以“去掉某一路后 fear 升高”不等于识别出恐惧。
2. **条件互换**（`swap_conditions.py`）：S06 十五秒三个条件之间互换某一路特征，结果跟着音频走。
3. **音频尾段**（`audio_tail_swap.py`）：generic_review 后 5 秒带背景音乐，被判成 sadness 96.4%；把这一段静音后变成 anger 56.3%。结论：比较条件时音轨必须一致。
4. **真人片段组合**（`film_clip_combos.py`）：对 Charade 片段只保留若干路、互换其他片段的某一路，解释为什么亲密片段的最高类是 fear。
5. **排查特征**（`audio_check.py`、`asr_all.py`、`face_probe.py`）：音轨响度、BEATs 标签、Whisper 转写、人脸检测输出。人脸分支对动画角色几乎输出常数：44 条项目视频之间的差异只有 6 条真实片段之间的约 1/9。
6. **探索性代理**（`dim_audio.py`、`text_go.py`）：语音唤醒度/支配度/情感价只能把敌对和亲密分开（差距很小），分不出紧张；GoEmotions 文本模型对明显敌对的台词几乎没有反应。均不适合作指标；这两条探索的原始输出没有保留，这里只留结论和脚本。
7. **恐惧专项**（S09、S15 共 6 条视频，`feature_swap_fear.py`，输出 `results/fear_feature_swap_s09_s15.txt`）：
   - 去掉对白文字、人脸或屏幕文字，fear 最多约 18%，不翻盘；去掉音频 fear 反而降到 2–9%。
   - 把真实恐怖片段（Night of the Living Dead，fear 99.6% 和 78.5%）的视觉特征换进来，fear 全部升到 94.9–99.7%；反过来把 S09、S15 的视觉特征放进该片段，fear 掉到 1.5–5.4%，变成惊讶 41.5–64.1% 和愤怒 29.2–55.0%；换音频则得到愤怒或惊讶，不是恐惧。
   - 结论：决定性的一路是视觉特征。局限：交换会产生拼接出来的特征，只能说明哪一路起作用，不能证明因果。
8. **变暗对照**（`darken_and_eval.py`，结果 `results/dark_experiment.json`）：ffmpeg 只降亮度，音频不变。

| 视频 | 原始 fear | 亮度 −0.30 | 亮度 −0.50 | 平均亮度（0–255） |
|---|---|---|---|---|
| S09 baseline | 7.5 | 19.8 | 87.1 | 91 → 18 → 4 |
| S09 generic_review | 5.5 | 26.7 | — | 未测 |
| S09 moodcut | 8.5 | 57.1 | — | 未测 |
| S15 baseline | 9.5 | 19.4 | 91.6 | 98 → 21 → 3 |
| S15 generic_review | 4.6 | 22.6 | — | 未测 |
| S15 moodcut | 8.5 | 19.8 | — | 未测 |

只降亮度，fear 全部上升，说明恐惧判断对亮度敏感；但 −0.30 已经很暗，−0.50 接近全黑，此时 fear 87–92% 只是模型对无信息输入的默认输出。变暗是恐怖片的典型线索，模型可能只是在响应“暗”，不能说明视频传达了恐惧。没有补跑更温和的档位。

## 6. 六种情绪的 VEMOCLAP 结果（S07–S12、S15）

加粗为目标情绪的概率（%）。S08、S10、S11 的 baseline 与 generic_review，以及 S12 的三个条件，是同一个视频文件。S15 来自“审查挑战”批次，baseline 是人工故意写得偏弱的初稿，**不能当作没有提示的模型基线**。

| 故事 | 目标 | 条件 | anger | disgust | fear | joy | sadness | surprise | 最高类 |
|---|---|---|---|---|---|---|---|---|---|
| S07 | 愤怒 | baseline | **80.9** | 13.1 | 5.8 | 0.0 | 0.1 | 0.0 | 愤怒 ✓ |
| S07 | 愤怒 | generic_review | **55.5** | 40.6 | 3.8 | 0.0 | 0.1 | 0.1 | 愤怒 ✓ |
| S07 | 愤怒 | moodcut | **95.7** | 4.0 | 0.2 | 0.0 | 0.0 | 0.0 | 愤怒 ✓ |
| S08 | 厌恶 | baseline | 19.6 | **68.6** | 0.5 | 0.0 | 8.6 | 2.6 | 厌恶 ✓ |
| S08 | 厌恶 | generic_review（同 baseline 文件） | 19.6 | **68.6** | 0.5 | 0.0 | 8.6 | 2.6 | 厌恶 ✓ |
| S08 | 厌恶 | moodcut | 8.0 | **84.6** | 0.2 | 0.0 | 6.0 | 1.2 | 厌恶 ✓ |
| S09 | 恐惧 | baseline | 44.3 | 3.1 | **7.5** | 0.0 | 41.0 | 4.1 | 愤怒 ✗ |
| S09 | 恐惧 | generic_review | 66.3 | 1.4 | **5.5** | 0.0 | 25.5 | 1.2 | 愤怒 ✗ |
| S09 | 恐惧 | moodcut | 62.1 | 5.1 | **8.5** | 0.0 | 13.5 | 10.9 | 愤怒 ✗ |
| S10 | 喜悦 | baseline | 5.6 | 1.1 | 0.2 | **0.2** | 5.0 | 87.9 | 惊讶 ✗ |
| S10 | 喜悦 | generic_review（同 baseline 文件） | 5.6 | 1.1 | 0.2 | **0.2** | 5.0 | 87.9 | 惊讶 ✗ |
| S10 | 喜悦 | moodcut | 15.3 | 0.5 | 0.2 | **0.3** | 3.4 | 80.4 | 惊讶 ✗ |
| S11 | 悲伤 | baseline | 17.6 | 45.8 | 2.4 | 0.2 | **27.7** | 6.4 | 厌恶 ✗ |
| S11 | 悲伤 | generic_review（同 baseline 文件） | 17.6 | 45.8 | 2.4 | 0.2 | **27.7** | 6.4 | 厌恶 ✗ |
| S11 | 悲伤 | moodcut | 29.4 | 5.9 | 0.7 | 0.0 | **63.7** | 0.3 | 悲伤 ✓ |
| S12 | 惊讶 | 三个条件（同一个文件） | 4.7 | 2.9 | 4.7 | 1.9 | 48.1 | **37.6** | 悲伤 ✗ |
| S15 | 恐惧 | baseline | 59.5 | 4.9 | **9.5** | 0.1 | 19.9 | 6.2 | 愤怒 ✗ |
| S15 | 恐惧 | generic_review | 29.9 | 5.1 | **4.6** | 0.1 | 54.5 | 5.8 | 悲伤 ✗ |
| S15 | 恐惧 | moodcut | 45.7 | 3.5 | **8.5** | 0.1 | 40.7 | 1.6 | 愤怒 ✗ |

- 愤怒（S07）和厌恶（S08）所有条件都命中，moodcut 的目标情绪比例更高；但李靖、太乙在敌对剧本里 disgust 也偏高，S08 的命中不能排除是角色画面造成的。
- 悲伤（S11）只有 moodcut 命中，只有一个故事，不能当结论。
- 惊讶（S12）三个条件是同一个文件，无法比较；组内人工观察画面里读不出悲伤，所以模型的悲伤判断是误判。
- 喜悦（S10）joy 只有 0.2–0.3%，被判成 surprise；组内人工观察喜悦很明显，只是和惊讶无法区分。日常场景里这两类本来就难分，“刚得知好消息”的剧情也自带意外。
- 恐惧（S09、S15）两个剧本、中英文、不同角色，fear 都只有 4.6–9.5%，三个条件没有差别。S09 的剧本规定白天、不展示生物、不尖叫不发抖，可见线索几乎只剩对白。

“组内人工观察”是项目成员看视频后的口头判断，不是盲评。

## 7. 氛围方案下的 VEMOCLAP 与 VBench

氛围方案（S01、S03、S04、S05、S06 以及更早的 Anna/Elsa 试点）的 29 条记录、含各路消融结果见 `results/vemoclap_all.json`。VBench 画面质量见 `results/vbench_scores.json`（28 条，含网站 S06 视频）。

- 12 组里 moodcut 比 baseline 高 5 组、低 7 组，中位数 −0.0055；5 秒的 5 组全部略低。画面不由 MoodCut 修改，三个条件视频由生成模型分别生成，差异主要是生成的随机性，不能当作方法效果。
- 自动评测的已知问题：音频主导且易被背景音乐翻转；亲密＝其余全部，得分容易接近 100% 而饱和；surprise 与角色画风（Frozen 角色）混在一起；缺失特征补零偏向 fear；每个条件只有一个视频。
- S07–S12、S15 还没有跑 VBench。

## 8. 复现

1. 按 [docs/vemoclap.md](../../vemoclap.md) 准备 VEMOCLAP 运行环境，按 [docs/vbench.md](../../vbench.md) 准备 VBench 环境。
2. 设置 `VEMOCLAP_UPSTREAM`、`MOODCUT_EVAL_WORK`、`MOODCUT_VEMOCLAP_CACHE`，把视频放到 `<MOODCUT_EVAL_WORK>/videos/<video_id>.mp4`，哈希必须与 `video_manifest.json` 一致。
3. `python scripts/emotion_eval/run_vemoclap_batch.py`，再 `python scripts/emotion_eval/collect_results.py`，即可重新生成 `results/` 下的文件；其余脚本见 [scripts/emotion_eval/README.md](../../../scripts/emotion_eval/README.md)。
4. 不需要模型的检查：`python scripts/emotion_eval/analyze_mapping.py` 和 `python -m unittest discover -s tests -p "test_emotion_eval_results.py"`。

## 9. 目录

| 路径 | 内容 |
|---|---|
| `video_manifest.json` | 50 条视频：故事、目标、条件、时长、语言、SHA-256、结果目录、相同文件关系 |
| `results/vemoclap_all.json` | 每条视频的六类概率、逐路去掉和只保留的结果 |
| `results/vbench_scores.json` | VBench imaging_quality 分数 |
| `results/dark_experiment.json` | 变暗对照 |
| `results/fear_feature_swap_s09_s15.txt` | 恐惧专项特征交换的完整输出 |
| `results/film_clips_vemoclap.json` | 真人电影片段的 VEMOCLAP 结果（片段本身不提供） |
| `protocols/` | 人工盲评方案草案、事先冻结的规则 V2、S09 探索性第二版草稿 |

## 10. 局限

- 全部结果是开发期描述性数据：每个条件一个视频、一次 CPU 离线运行，没有人工盲评；换机器或软件版本没有验证。
- 每种情绪只有一个故事，情绪、剧情、角色和影片绑在一起，只能在同一故事内比较三个条件。
- 真人电影片段的目标标签最初只看了截帧和自动字幕，没有核实台词，其中几个标签不符或存疑，所以那套校验的证据比表面上弱；片段版权状态未确认，不随仓库提供。
- 部分目标氛围是推定的（S06 十五秒视频、Anna/Elsa）。
- 视频文件的版权和来源遵循仓库已有的素材规则，不在这里重新分发。
