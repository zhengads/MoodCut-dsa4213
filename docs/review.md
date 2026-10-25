# 审查实现：报告验证、原子补丁与全局复查

[演员协议](ACTOR_REVIEW_METHOD.md)说明当前 v3 方法；本页说明共用验证器和兼容的 `global_v1` 路径。准确字段见 [CONTRACTS](CONTRACTS.md)。

既有报告/补丁与全局审查基础实现由 FAN XUYANG 交付；生成式台词限定适配由 ZHENG MINGLIANG 交付。后续演员协议与来源重检保留各 PR 的贡献记录。

## 报告与补丁

`validate_report` 检查版本、场景、模式、非空且唯一的 issue ID、镜头引用、维度、证据、建议和严重程度。空意见合法；结构检查无法证明模型意见真实或语义充分。

`apply_patch` 先复制输入，再原子应用补丁：每镜头最多一条 edit，issue 必须关联该镜头。任一错误整体拒绝并返回原计划的独立副本，不返回半修改结果。候选必须通过公共 `validate_plan`；验证器缺失、异常或返回格式错误均不能绕过。

| 输出模式 | 允许修改 |
| --- | --- |
| 默认 animatic | dialogue、narration、duration_s、visuals.crop；素材身份与顺序不变 |
| 显式 generated | 仅 dialogue；完整非台词内容（包括扩展字段）不变 |

generated 不投影越权候选，不从被丢弃的版本继承复查结论。演员协议还冻结说话人、顺序、行数，并核对反馈所属行；详见[方法](ACTOR_REVIEW_METHOD.md)。

## 全局审查的阶段与失败语义

两组接收同一故事、目标 tone 和初稿；使用相同模型配置、修订/复查模板和输出上限，只有审查准则不同。每阶段最多调用一次。

| 路径 | 阶段 | 结果 |
| --- | --- | --- |
| 输入或 mode 非法 | 无 | review_failed |
| 无意见 | critique | unchanged，空补丁，verification=null |
| 补丁或候选非法 | critique → revise | rejected，整体回退 |
| 合法候选 | critique → revise → verify | applied；无实际变化则 unchanged |
| 模型/API/JSON/报告/复查失败 | 截至失败阶段 | review_failed，保留诊断，不重试 |

同镜头意见通过 `issues_by_shot` 汇集；仍保留全部原始 ID。复查必须以互斥、完整的 resolved/unresolved ID 集合覆盖原意见；空补丁有意见时也要复查。未解决意见和新问题保存于 verification，不触发额外调用。applied 不是情绪改善结论。

`review.json`、`final.json` 和实际复查候选保持一致。日志保留已获得的报告、补丁、复查结果与错误；原始文本留存由公共客户端的 PRIVATE 响应目录负责，见 [CONTRACTS 6.22](CONTRACTS.md#622-private-text-response-retention-and-json-diagnostics)。旧失败中缺失的原文不能事后重建。

## 使用与验证

默认函数调用保持 global_v1；生成式模式需显式传参：

```python
result = review_and_revise(
    scene, initial, manifest, client,
    mode="moodcut", project_root=".", output_mode="generated",
)
```

离线验证使用已有 FakeClient 和夹具：

```powershell
.venv/Scripts/python -m pytest tests/test_patches.py tests/test_reviewer.py -q
```

命令是验证入口，不表示本次文档整理重新执行过该测试集。软件夹具、模型自评和人工评分分开解释；早期验收与演示代码见[历史索引](history/README.md)。
