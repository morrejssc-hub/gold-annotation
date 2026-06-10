# Atlas 卡片字段标准

每张卡 = 一个 `.md`：**YAML frontmatter（字段）** + **正文（带火候的散文段，`## 段名` 分节）**。
字段从 `bible_v2.2` 抽出，不发明。编译器 [`../compile.py`](../compile.py) 单向 Atlas → `runtime.md`。

## frontmatter 字段

| 字段 | 必填 | 进 Runtime | 含义 |
|---|---|---|---|
| `id` | ✓ | ✓(作 anchor) | kebab-case 唯一键 |
| `label` | ✓ | ✓(作标题) | 人读名，**只索引、不发令**（GPT："标签可留名，机制才发令"） |
| `type` | ✓ | 见投影纪律 | **Decision 层**：`spine`（脊柱状态变量，常驻）/ `trigger`（if-then 触发卡）；**皮肉层**：`substrate`（角色本体实例）/ `voice`（语气轨）——后两者仅 `--mode prod` 合并 |
| `trigger` | trigger 必填 | ✓ | 触发谓词，**写在接地原语轴上**：`对象 / 在场结构 / 信任态 / 情绪压强 / 关系期待`（spine 无） |
| `modulated_by` | — | ✓(渲染为"受…调制") | 本卡受哪些脊柱变量调制（如 `[trust]`）。**耦合靠链接，不靠复制** |
| `status` | ✓ | **过滤**(仅 promoted 进) | `promoted` / `pending`（待验证池） |
| `anchors` | promoted 必填 | ✗剥 | 原文 uid 锚（铁律4），如 `卷4_12_134` |
| `source` | ✓ | ✗剥 | 来源人判，如 `item09→v2.1` |

## 正文段（`## 段名`）

- **进 Runtime**：`内部判断`、`外显策略`、`禁止`、`调制`（spine 用）、`定义`（spine 用）——即除下面外的所有段。
- **Atlas-only（编译剥掉）**：`例子`、`笔记`、`出处说明`。

## 卡边界判据（拆 / 合）

**前提**：当前所有卡**打包进 context 整体发给 agent**，无检索/RAG、无单卡隔离（[[exp2]] 想法1：单角色缓检索引擎）。→ **卡边界是编写/维护问题，不是 runtime 问题。** 不为"隔离/整洁"而拆。

只看两条：
1. **字段是否真分叉**：`trigger` 不同 **或** `外显策略` 不同 → 拆；触发与策略都一样 → 合。
2. **生命周期 / 修改频率**：会被**独立修改 / 不同节奏迭代** → 拆；总是一起动 → 合（如 `core` 的 want/need/wound/lie 永远一起改 → 一张）。

`type`（spine/trigger）本身也只是字段差异（有无 `trigger` 谓词），同理。

## 晋升闸

`status: pending → promoted` 的条件：`(触发 + 内部判断 + 外显策略 + 禁止)` 四栏填满 **且** 过一次 rollforward 盲判。脊柱变量的"四栏"对应 `定义 + 调制 + 禁止`。未达标留 `pending`，不进 Runtime。

**锚的现实**：部分卡源自 exp1 **skill 定型前**的早期工作，原测试在另一台机器、判定已过时未提交 → 锚一时补不齐。这类记 `anchors: []` + `## 笔记` 注明"锚待补"，**仍可 promoted**（它们活在 bible_v2.2、不回归）。[`check.py`](../check.py) 把"promoted 但缺锚/缺栏"列为 **lint 警告（不阻断）**，提示日后补，不挡发布。

## 投影纪律（评测态剥离 / 生产态合并）

**核心原则：剥离是编译模式，不是对源的一次性 sweep。** 本体论是 core.wound→lie 的根、**留在真源剥不得**；它作 `type: substrate` 一等层活在 Atlas，由 `compile.py --mode` 决定进不进投影。同一 Atlas 出两个投影：

| 模式 | 进投影的层 | 用途 |
|---|---|---|
| `--mode eval`（默认） | 只 Decision（spine+trigger） | **去名词留结构**：验决策机制 substrate-independent。这是反 recall 评测的公平投影——把 capstone（白领上司测试）从手搓场景升级成系统投影。 |
| `--mode prod` | Substrate + Decision + Voice 分层合并 | **披回皮肉但保持源码分层**：本体设定 / 决策机制 / 语气轨各成一段，非熔回单体散文。 |

**身份只活在 Substrate/Voice 层**——Decision 卡正文（定义/内部判断/外显策略/禁止/调制）一律**本体无关**：
1. **纯记忆**（罗伦斯/约伊兹/某商人）→ 决策卡里写**角色槽**（高信任伴侣/对象/对手），具体实例由 substrate `## 槽绑定`。
2. **本体身份**（不死/被供奉为某象征又被弃/异类/皮可剥卖/兽耳狼尾）→ 决策卡里写**抽象形状**（"被供奉的某种象征"/"非台词的体征通道"），具体实例由 substrate `## 本体`/`## 体征通道`。
3. **行为机制**（信任调制、漏→封顶→夺回、时序闸）→ 本就身份无关。

这把"去身份"从靠人盯的编写纪律，变成**结构强制 + lint 守**：`check.py` 的反 recall lint 扫每张决策卡的会编译段，内联专名/体征专名/语癖字即告警（capstone 自动化）。编写/研究 meta → `笔记`，例子与锚句 → `例子`，皆 Atlas-only。

## 不变量（违反即重蹈 exp1/exp2 覆辙）

1. **trust 等状态变量是脊柱、用 `modulated_by` 链接**，绝不复制进每张触发卡（exp2：保留压缩，防组合爆炸 + 切断耦合）。
2. **触发写在接地原语轴上**（对象/在场/情绪压强…），不枚举具体情景（exp1：压缩不枚举，卡是基向量不是点）。
3. **Runtime 不编码散文规则**（留白/节奏/show-don't-tell）——那是语气轨，走 voice_gold/LoRA。
4. **身份只活在 substrate/voice 层，决策卡正文本体无关**（剥离在投影不在源；check.py 反 recall lint 守）。违反 = 评测态靠 recall 蒙混、证不了 substrate-independent。
