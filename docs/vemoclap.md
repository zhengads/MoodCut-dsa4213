# VEMOCLAP 本地视频情绪概率接线

本增量属于 [Issue #9](https://github.com/zhengads/MoodCut-dsa4213/issues/9)，作者 FANXUYANG，2026-10-25。
提供 `python -m moodcut.vemoclap` 独立入口：读取已有视频，调用本地 VEMOCLAP，保存六类原始 softmax 概率。
VEMOCLAP 是预训练视频情绪分类器，并非新建的数据集；这里是辅助诊断接线，不接管原有人工评分、资格复核或 VBench。

## 输入与输出

输入为已有 P4 成片 `film.mp4` 或单镜头 `generated.mp4` 的本地路径。
直接读取视频及其音轨；不把剧本、目标 tone、condition 或审查意见传给分类器。
可对 baseline / generic_review / moodcut 的实际视频分别调用，并为每次使用不同输出目录。
复用的相同视频可按 SHA-256 识别，但本入口不把多次调用当作独立样本，也不做组间统计。

输出目录包含：

- `result.json`：状态、输入文件名/字节数/SHA-256/时长、上游版本和关键文件哈希、环境检查，以及成功时的 `probabilities`、`top_emotion`、缺失特征与包版本。
- `worker-result.json`：实际调用 worker 时产生的未取整概率；失败时可能为空或不存在，不作为成功结果使用。
- `worker.log`：实际调用时的本地诊断日志。可能含本机路径，不上传 GitHub 或发给观看者。

`probabilities` 的键固定为 `anger/disgust/fear/joy/sadness/surprise`，每项为 0–1 数值，和约为 1。
不是百分数文本解析，不强制重新归一化异常结果。`top_emotion` 只是最大值标签，完整分布始终保留。
不自动映射 affectionate/suspicious/hostile/tense；六类概率不能直接证明亲密、敌对或紧张关系氛围命中。

默认仅预检。状态为 `checked_not_run` 时概率仍为 null，表示基础文件/模块/媒体检查通过，未证明模型缓存齐全或能够推理。
缺依赖为 `blocked`，执行/输出校验异常为 `failed`，两者 CLI 均返回 1、概率为 null。
仅真正的 worker 正常返回且概率/输入身份检查通过才为 `success`。
软件测试使用独立的合成 worker，不出现在生产入口中，不存在失败后自动补造分布的路径。

## Windows / PowerShell 用法

在此分支的 MoodCut 根目录运行，使用本分支安装的 Python 环境。
独立 worktree 的 `.venv` 不会自动继承另一个工作目录的依赖；不要通过重新安装来改变另一个工作流正在使用的环境。
先按根 README 在当前目录创建环境并安装 `.[dev]`，将 FFmpeg 与 ffprobe 加入 PATH。

VEMOCLAP 源码保持在项目外部或已有忽略的 `references/upstream/` 缓存内；不提交源码副本、模型或媒体。
使用现有下载的 `video-emotion` 仓库，固定版本为
[`312f80204f001d611564a2c8405999080829cae3`](https://github.com/serkansulun/video-emotion/tree/312f80204f001d611564a2c8405999080829cae3)。
检查原 checkout 的版本和修改；版本不一致时准备独立副本，不覆盖已有副本的工作。

```powershell
.venv/Scripts/python -m moodcut.vemoclap --help
.venv/Scripts/python -m moodcut.vemoclap --video runs/existing/baseline/film.mp4 --upstream ../video-emotion --source-kind provided_local --output runs/emotion-check-01 --check
```

预检不导入上游模块或 PyTorch，不下载模型。`provided_local` 仅声明本地提供文件，不能认证其为真实模型产物；软件媒体使用 `synthetic`。
本适配器要求有视频和音轨、时长大于 3 秒，实际解码后音频也需超过 3 秒，以避开上游 BEATs 空音频块边界。
这是本次接线的保守范围，不是论文宣称的视频时长限制。无固定最大时长；长视频的时间和内存需求尚未验证。

在**独立 VEMOCLAP 环境及模型缓存准备完毕后**，显式运行一段 CPU 推理：

```powershell
.venv/Scripts/python -m moodcut.vemoclap --video runs/existing/baseline/film.mp4 --upstream ../video-emotion --python runs/vemoclap-runtime/venv/Scripts/python.exe --cache-dir runs/vemoclap-runtime --source-kind provided_local --output runs/emotion-cpu-01 --run --timeout 1200
```

`--python` 指向已配置的模型环境解释器；默认使用当前解释器。相对路径相对于调用时的工作目录。
`--cache-dir` 指定模型与临时文件的共同根目录。HF、PyTorch、Surya、CLIP、Matplotlib、字节码和临时文件均绑定到该目录；未指定时使用 `MOODCUT_VEMOCLAP_CACHE` 或输出目录旁的 `vemoclap-cache`，不默认写用户主目录。
每次输出必须是新目录，禁止写到上游源码目录内。超时后保留失败，不重试、不切 GPU、不调用外部 API。
默认隔离进程隐藏 CUDA、固定 CPU/两线程，启用 Hugging Face 离线设置并拒绝 Python 网络连接。
本入口没有下载/安装功能；缺缓存直接失败。不会生成新视频或改动原始 RunRecord、账目、人工评分及 comparison 状态。

已准备本地环境时，也可从项目根目录使用 PowerShell 入口（FFmpeg/ffprobe 需在 PATH）：

```powershell
./scripts/run_vemoclap.ps1 -Video runs/existing/baseline/film.mp4 -Output runs/emotion-cpu-02
```

加 `-Check` 只预检，`-Runtime` 可指定另一份独立环境。默认解释器为 `runs/vemoclap-runtime/venv/Scripts/python.exe`。

2026-10-25 的独立 Windows 环境使用 Python 3.13.5、CPU PyTorch 2.7.0 / torchvision 0.22.0 / torchaudio 2.7.0、Transformers 4.56.2、Surya 0.16.7；完整版本见 [CPU 环境清单](../configs/vemoclap-cpu-requirements.txt)。
安装前把 `TEMP`、`TMP`、`PIP_CACHE_DIR` 设置在选定盘符的运行目录；先安装 `setuptools==78.1.0` 和 `wheel`，再使用 `pip install --no-build-isolation -r configs/vemoclap-cpu-requirements.txt`。
`--no-build-isolation` 使固定版 CLIP 使用已安装的 setuptools，避免新版隔离构建缺少 `pkg_resources`。不要在另一个工作流的解释器中安装。

## 环境准备与适配边界

仅下载上游 Git 仓库不足以推理。初次副本只有最终分类器及配置/stats；本次继续配置后已补齐以下依赖和模型：

- Python 特征模型依赖，包括 PyTorch、torchvision、torchaudio、transformers、CLIP、Surya OCR 等；预检报告列出当前解释器缺失模块。
- `weights/yolov5m-face.pt`。
- `src/beats/pretrained_models_labels/BEATs_iter3_plus_AS2M_finetuned_on_AS2M_cpt2.pt`。
- CLIP、ASR、文本情感、人脸情绪、语言识别/翻译及 Surya 的模型缓存。固定来源、版本、文件大小及模型 SHA-256 见 [模型清单](../configs/vemoclap-models.json)；HF 大权重下载后按发布的 LFS SHA-256 核对，其余辅助文件记录实际下载哈希。

上游 README 的 `files/requirements.txt` 在固定版本中不存在，仓库实际提供的是 `requirements_colab.txt`，其中采用 CUDA 11.8 构建，且未枚举源码所有直接导入的包。
本增量使用上述独立 CPU 环境清单，未直接安装这份 Colab 配置。实际完整离线推理记录见下节。

worker 复用上游模型类和抽帧/归一化函数，保留原特征顺序、缺失特征补零、序列重采样/补齐及分类器权重。
移除与分类无关的 caption/图窗，使用显式 softmax 维度并保留精度；空列表检查不再与 tensor 做直接相等比较。
使用 CPU float32（不启用 CUDA AMP）、显式 eval 和 BEATs `num_workers=0`，适应 Windows 独立进程。
上游 config/stats 中保存的 `pathlib.PosixPath` 通过专用 Unpickler 转为当前平台路径，避免 Windows 反序列化失败；不改写原始模型文件。逐特征释放模型并回收 Python 对象。
这些变化不构成对原 GPU 输出的逐值等价验证；`missing_features` 会披露补零的特征，构造器/依赖错误仍为失败。

## 验证记录

离线验收命令：

```powershell
.venv/Scripts/python -m pytest tests/test_vemoclap.py -q
```

2026-10-25：29 项通过，覆盖六类分布验证、实际子进程接线（明确的合成 worker）、失败/超时/异常 JSON/视频变化拒绝、输出不覆盖、源码版本与修改拒绝、默认不推理、相对 Python 环境路径、CLI 失败退出码、Linux 路径元数据跨平台读取、缓存/临时目录隔离，以及 FFmpeg 创建的 4 秒软件音视频预检。
这些测试没有运行真实特征提取器或分类器，不是情绪效果数据。

现有 P5 回归与首轮适配器测试合跑：124 项及 92 个子测试通过（152.71 秒，其中首轮适配器为 23 项）；后续路径/CLI/时长边界增补后，适配器 28 项单独通过。
33 份锁定参考文件校验、CLI help 和提交差异格式检查通过。未声称完整仓库 CI 通过。

### 单段真实 CPU 技术验证（2026-10-25）

初次预检为 `blocked`；随后获得继续配置环境并验证单段视频的授权，完成上述依赖/模型准备。
使用同一段已有 Anna/Elsa actor-v1 moodcut 原片，时长 5.258344 秒，文件 SHA-256
`cf0aaaf662f76df3ca2166ce33f2690663451783fba068b5346b5efc5dc771c8`。
原片来源：[历史试跑说明](pilots/anna-elsa-actor.md)与 [Release](https://github.com/zhengads/MoodCut-dsa4213/releases/tag/pilot-anna-elsa-20261024)。

实际结果 `status=success`，CPU/两线程，适配器总耗时 **197.596 秒**（含预检、加载和推理，不含下载/安装）。
ASR sentiment、BEATs、CLIP、face emotion、OCR sentiment 均完成，`missing_features=[]`。
网络连接在 worker 中被禁止；视频和上游已跟踪文件在运行后身份检查通过。
全部依赖、模型缓存、下载和临时文件均在选定的非系统盘运行目录，已清理 7.38 GiB 下载分块副本。

| 原生类别 | 实际 softmax 概率（表中取小数） |
|---|---:|
| anger | 0.0188516993 |
| disgust | 0.0028474140 |
| fear | 0.0055828085 |
| joy | 0.0001153563 |
| sadness | 0.0115967644 |
| surprise | 0.9610059857 |

完整精度与日志保留在本地忽略目录 `runs/vemoclap-real-cpu-01/`：`result.json`、`worker-result.json`、`worker.log`。
本次模型清单 SHA-256 为 `a322cd3eed0fab9fccfea16ece8186291a0befb7167e8a7eb6d64c54ff0a9e7a`，与结果绑定。
复现时使用同一视频、固定环境与清单，输出选择新目录；已准备好的本地环境可运行：

```powershell
./scripts/run_vemoclap.ps1 -Video runs/existing/actor-v1-moodcut.mp4 -Output runs/emotion-cpu-next
```

这是单段真实视频到模型概率的技术验证，最高类别为 surprise；不是亲密/敌对/紧张的识别准确率，也不说明哪种审查方法更好。
没有新生成视频、付费 API、GPU 推理、人工评分或正式实验。原有三条件评分、账目和正式纳入规则保持原义。

## 上游署名

Serkan Sulun、Paula Viana、Matthew E. P. Davies，
[VEMOCLAP: A Video Emotion Classification Web Application](https://arxiv.org/abs/2410.21303)。
上游作者/版权及 GPL-3.0-or-later 许可全文保存在 [vemoclap-LICENSE.md](licenses/vemoclap-LICENSE.md)，仅整理行尾空白。
`src/moodcut/vemoclap_worker.py` 的推理顺序参考上述固定版本的 `video_emotion_classifier.py`，保留版权/许可并明确 FANXUYANG 的适配修改。
未将原作者代码、模型或项目已有贡献改署本轮作者。
