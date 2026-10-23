# 还伞试跑：合成人物素材来源与署名

关联：[#8](https://github.com/zhengads/MoodCut-dsa4213/issues/8)、[#9](https://github.com/zhengads/MoodCut-dsa4213/issues/9)。本次仅授权离线适配；素材、故事和手写台词不是独立模型效果证据。实际视频执行仍未批准。

## 来源与允许范围

作者 Ariel Bravo Ayala，项目 [sigils-people](https://github.com/ambravo/sigils-people/tree/0a411d71ccf1f8b599c5e48f03039f29b5f63490)，固定提交 `0a411d71ccf1f8b599c5e48f03039f29b5f63490`。肖像适用 [LICENSE-PORTRAITS](https://github.com/ambravo/sigils-people/blob/0a411d71ccf1f8b599c5e48f03039f29b5f63490/LICENSE-PORTRAITS)，不是代码的 MIT 许可。来源声明肖像为 RealVisXL 生成的合成人物，不据此担保不存在任何相似性或权利争议。

该文件明确允许署名后复制、再分发、改编，包括商业用途，列明 CC BY 4.0 及来源附带的可接受使用条款。须保留作者、来源、许可链接、合成人物声明，并说明转换/改编；不能冒充真实人物、证言或可识别在世人士，也不能用于骚扰、伤害性虚假信息等被列明用途。完整条款随原图保存并校验，不将其简化为“完全无限制”或用“合成”代替来源核对。

当前采用范围：林/博两个**虚构角色**的共同身份和服装参考，仅用于已提议的还伞技术预检。原记录中的人名、国别、年龄和自动 review 不作为真实身份、独立人口属性核验或质量证据，不导入故事人物信息。

## 必须随材料保留的署名

Portraits by [Ariel Bravo Ayala — sigils-people](https://github.com/ambravo/sigils-people) — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Synthetic people; not photographs of anyone.

改编说明：原 AVIF 解码为 RGB 后另存 PNG；未裁切、缩放、修图或重生成人脸。后续若用于视频，应补记生成式动画、虚构场景和台词的改编，不暗示原作者背书。

未来发放观看/匿名材料时附上相同的公共 credits，不能只留在 PRIVATE 或内部试跑单。各条件署名一致，不包含方法标签、目标 tone 或映射，不在画面内增加字幕；沿用既有匿名视频/评分入口。原图/XMP 保留，PNG 亦带来源、原始哈希、署名、许可及合成人物标记。转码不能作为去除署名或来源声明的手段。

## 文件身份与适配

完整路径、尺寸、文件大小、来源/转换哈希和解码 RGB 像素哈希见[锁定清单](../../assets/pilots/umbrella-sigils.lock.json)。本地素材在忽略目录 `assets/raw/sigils-people/`；原图、转换图及完整上游许可不提交 Git。

| 文件 | 角色绑定 | 原 AVIF SHA-256 | 转换 PNG SHA-256 |
| --- | --- | --- | --- |
| cn-02 | `lin_portrait` → 林 / lin | `f336e635cfd8a6bf706d25ca249a5ae1cd610254dd3dcd6224881b68fff265a6` | `f2508d4736f673f89de15521e853981f3b7b1762cfa64773120bbd313b75229b` |
| cn-04 | `bo_portrait` → 博 / bo | `c0aa989763acb80ed61d5ad286baf57ec943ea9756119cea12085782a4bb0730` | `4e3cf08c9cafafdbc5c13419cae0933948432a4b46702527779a0f58091a19a5` |

两张均为 1024×1024。cn-02 为条纹上衣/背包参考，cn-04 为红色开衫参考；按原模板匹配各自身份和服装，不能复制屋顶/室内背景替代雨天公交站或照搬自拍构图。手臂、下半身及递伞动作并非由肖像提供，仍须生成后人工验收。三条件使用相同图像顺序、角色绑定、全图裁切、声音、镜头、时长和 seed；只改台词。

转换使用 Pillow 12.3.0 / libavif 1.4.2，PNG compress_level=9、optimize=false，保留原 XMP/ICC（若有）。比较的是**原图解码后的 RGB 像素**与 PNG 解码像素；不把文件哈希相等当转换成功标准，也不宣称 AVIF 本身未经历有损编码。不同编码器/版本若导致字节或像素不符，脚本停止并保留文件，不自动更新锁值。

## 复核命令与剩余门禁

使用支持 AVIF 的 Pillow；项目旧的 Pillow 10 环境未必具备解码器，不自动升级或下载模型。仓库根目录执行：

```bash
# 首次明确获取固定公开来源（约232KB），再做本地转换；不调用模型
python scripts/prepare_umbrella_assets.py --fetch
# 已缓存时只转换/验证，不联网，不覆盖已有文件
python scripts/prepare_umbrella_assets.py
# 只读核对来源、转换、清单和原编译器的三条件共同输入
python scripts/prepare_umbrella_assets.py --check
```

脚本复用既有参考下载校验、素材 manifest 构建器及 P4 编译器，不导入或执行上游生成程序。清单中的 `source_url` 是**转换 PNG 的离线交付占位地址** `example.invalid`；原 AVIF URL 单独记录为 `origin_url`，不能把两种字节混绑。当前没有上传/托管图片，也没有证明提供商可取得 PNG。

部署可读 PNG 后，须核对远端与本地转换字节一致，在新目录重算共享/请求身份；当前离线身份不能沿用为真实运行冻结值。历史未知费用、当前余额、运行/听看负责人、模型/范围/预算及真实任务仍待确认，执行批准保持 false/null。无付费 API、真实任务或人工评分。
