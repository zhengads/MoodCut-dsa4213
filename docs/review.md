# MC-03：报告检查、原子补丁与一次审查复查

负责人：FAN XUYANG。PR 1 实现 `validate_report(scene, plan, report)` 与契约中的
`apply_patch(scene, plan, manifest, report, patch)`。PR 2 实现
`review_and_revise(scene, initial_plan, manifest, client, *, mode)` 和四份审查提示。
本地验收均使用共享 FakeClient，未调用真实模型。

报告检查返回错误字符串列表：检查版本、场景、模式、每条意见的非空 ID、
镜头引用、证据、建议、维度、严重程度和唯一 issue_id。空 issues 合法。
证据须有具体内容，但程序无法证明意见真实或语义上足够具体。

补丁先 deepcopy，限制每镜头一条 edit，要求 issue_id 对应该镜头的报告意见。
只替换 dialogue、narration、duration_s 或 visuals 的 crop；素材列表和顺序保持。
任一错误返回原计划的独立副本、status=rejected 与 errors，不返回部分修改。
有效候选交由公共 validate_plan 检查，总时长、允许裁切、角色引用等以 MC-01
验证器为准。验证器缺失、抛异常或返回格式错误也整体拒绝，绝不绕过验证。
无修改且验证通过返回 unchanged；有效变化返回 applied。

## Windows / PowerShell 运行

在项目根目录执行：

```powershell
.venv\Scripts\python.exe -m pytest tests/test_patches.py tests/test_reviewer.py -q
.venv\Scripts\python.exe scripts/prepare_references.py --check
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_prepare_references.py" -v
```

Python 调用可从 `moodcut.reviewer` 导入 validate_report，从 `moodcut.patches`
导入 apply_patch。返回结果是 JSON 可序列化 dict，无文件写入或客户端调用。

## 示例修改记录（人工编写软件测试，非模型结果）

| 原台词 | 意见 | 修改后台词 | 验证状态 |
|---|---|---|---|
| I have read it. | 原台词过于中性，缺少怀疑线索 | Where did you get this letter? | 共享夹具及真实 validate_plan 验证通过，applied |

叙述始终是字幕，固定图片加裁切不代表生成了新动作。保留 beat_ids 不能证明
剧情含义未变；剧情、自然度和情绪效果仍需人工审阅，不能以结构通过代替。

## 当前依赖与验收边界

2026-10-14 已同步 main 至 bf87fbe（合入 P1 #13、P5 #14）。MC-01 的
validate_plan、FakeClient、共享 JSON 夹具及图片已经到位，原依赖缺失阻碍解除。
公共验证器默认按当前工作目录解析素材路径；新增可选 project_root，CLI 和 pipeline 显式传入项目根目录，避免调用目录影响校验。

tests/test_patches.py 的 SharedFixtureTests 直接读取共享夹具并调用真实
validate_plan，覆盖有效台词/裁切修改、无意见、相同值、时长上下限及非法数值、
manifest 裁切限制、角色与文本错误、素材 hash 错误、多镜头原子回退和输入不变。
单元测试中的 spy 仅用于公共验证器异常、返回格式与调用隔离等故障路径。
没有修改 MC-01 文件或共享夹具，也没有实现第二套公共验证器。

补丁入口额外拒绝 dialogue 中 character_id/text 以外的字段，拒绝 visuals 中
asset_id/crop 以外的字段；不允许通过嵌套字段夹带动作或其他越界修改。
CLI review 与三条件 pipeline 已接入该实现；可用 README 的离线命令核验。review_and_revise 与 apply_patch 支持可选 project_root，保持原有调用兼容。

## PR 2 执行与失败语义

两模式接收相同的 scene（包含目标 tone）、初稿和 manifest。generic_review
覆盖剧情、自然度、目标情绪和可实现性；moodcut 聚焦具体镜头与目标情绪的偏差。
两者共用修订和复查提示、同一执行函数及每次 2048 的 max_output_tokens。
模型由传入的公共 client 决定；调用者比较两模式时须提供相同模型配置，模块不会
自行选择或切换模型。每阶段最多调用一次，无自动重试。

| 路径 | 调用阶段 | 结果 |
|---|---|---|
| 输入或 mode 不合法 | 无 | review_failed，保留初稿和错误 |
| 无审查意见 | critique | unchanged，空补丁、verification=null |
| 补丁结构或候选计划不合法 | critique → revise | rejected，整体回退 |
| 正常修订 | critique → revise → verify | applied；实际无变化则 unchanged |
| 模型异常、非法 JSON、报告/复查格式错误 | 截至出错阶段 | review_failed，整体回退且不重试 |

复查的 resolved/unresolved ID 集合必须互斥且完整覆盖原意见，不允许重复或未知 ID。
未解决意见和新问题保留在 verification，不触发第四次调用，也不等同于修复成功。
空补丁仍复查；有效复查可以继续保留未解决意见。applied 只表示结构合法的补丁已应用，
不代表情绪效果得到独立证实。

返回值维持公共 ReviewResult 字段。已取得的 report、patch、verification 原样保留，
即使相应内容校验失败，也作为失败诊断保存；调用者须检查 status 和 errors。
`moodcut.review.trace` 日志逐项记录请求、原始返回 JSON、异常和实际调用次数。
公共 client 不暴露原始 HTTP 文本或解析失败前的内容，因此该内容不能由本模块恢复；
此类异常记录错误，不伪造响应。日志中没有费用数据，不能据调用次数推定实际费用相同。

## 离线演示与产物（PowerShell）

从仓库根目录运行以下代码，会在新建的 runs 目录保存两模式的完整 ReviewResult
和 JSONL 诊断日志。目录已存在时会报错，避免覆盖。每次运行使用新的时间后缀。
这不是正式模型实验，也不调用 CLI、VBench 或付费服务。

```powershell
@'
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "src")
from moodcut.client import FakeClient
from moodcut.reviewer import review_and_revise

fixtures = Path("tests/fixtures")
def read(name):
    return json.loads((fixtures / (name + ".json")).read_text(encoding="utf-8"))

out = Path("runs") / ("mc03-offline-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
out.mkdir(parents=True, exist_ok=False)
logger = logging.getLogger("moodcut.review.trace")
logger.setLevel(logging.INFO)
for mode in ("generic_review", "moodcut"):
    report = read("review")
    report["mode"] = mode
    client = FakeClient([report, read("patch"), read("verification")])
    handler = logging.FileHandler(out / (mode + ".jsonl"), mode="x", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    try:
        result = review_and_revise(read("scene"), read("plan"), read("assets"), client, mode=mode)
        with (out / (mode + ".json")).open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print(mode, result["status"], "calls:", len(client.calls))
    finally:
        logger.removeHandler(handler)
        handler.close()
print(out)
'@ | .venv\Scripts\python.exe -
```

## 本地状态记录（2026-10-14）

- 负责人 FAN XUYANG；工作分支 `p3提前测试`。同步 main 时无冲突，保留原 5 个
  MC-03 未提交文件；没有修改本地 main，没有 commit、push、创建 PR 或合并 PR。
- Windows / PowerShell，使用 `.venv\Scripts\python.exe`；补齐项目声明的
  Pillow 依赖，安装版本 12.3.0。同步后原测试为 86 passed、38 subtests passed。
- 当前增补真实集成与边界检查后的 MC-03 定向测试：25 passed、25 subtests passed。
- 最终全套离线测试：98 passed、50 subtests passed；`git diff --check` 通过。
  自查修改范围仅为 reviewer.py、patches.py、两份模块测试和本文件，公共接口签名
  与契约一致，未改其他成员模块。共享夹具有效修改返回 applied，非法修改整体回退。
- 33 份锁定核心参考资料已校验，无需下载；没有执行上游代码、调用付费 API、
  下载模型权重或运行真实 VBench。mock/夹具不作为情绪效果实验结果。
- GitHub 可读取 Issue #12，本次查询没有 assignee、认领评论或开放 PR。
  按本会话用户的负责声明开展本地工作。尝试发布本轮状态评论时返回
  HTTP 403 `Resource not accessible by integration`，远端评论和认领记录未写入。
  状态记录保留在本文件；需要具有写权限的连接或负责人手动发布至 Issue #12。
- PR 1 本地实现已包含公共验证器集成；PR 2 已完成四份提示、两模式同预算执行、
  一次复查、错误回退及诊断日志，仍为本地未提交状态。
- PR 2 定向验收：37 passed、25 subtests passed。覆盖两模式阶段顺序、最多三次调用、
  无意见提前退出、拒绝补丁、空补丁、未解决意见、新问题、各阶段队列耗尽及非法响应、
  超时不重试、非法复查完整回退、输入不变和 JSON 诊断记录。
- PR 2 最终全套离线验收：110 passed、50 subtests passed；33 份参考文件重新校验通过，
  `git diff --check` 通过。两模式演示均 applied、各 3 次 FakeClient 调用；结果与日志位于
  `runs/mc03-offline-20261014-213623-676847/`，已检查 JSON 可读性及每份日志的 7 条事件。
  runs 被 Git 忽略。最终修改仅涉及任务卡允许的 9 个文件，未修改公共接口、CLI 或配置。

方法参考 FilmAgent 的 stage1_verify/stage2_verify 和 director_3、director_4、
screenwriter_4、actor 提示（VideoClaw 固定提交
16c1ce0b553e30eff90ff1274e8a8a63c1d548a3，FilmAgent 子树）。本实现独立编写，
未复制上游代码或提示，未执行上游入口，不是原论文完整复现。
