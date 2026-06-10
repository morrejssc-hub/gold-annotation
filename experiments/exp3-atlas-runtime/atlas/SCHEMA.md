# Atlas 卡片字段标准（v2，exp4 re-type）

每张卡 = 一个 `.md`：**YAML frontmatter（字段）** + **正文（带火候的散文段，`## 段名` 分节）**。
字段从 `bible_v2.2` 抽出，不发明。编译器 [`../compile.py`](../compile.py) 单向 Atlas → `runtime.{eval,prod}.md`。
v2 变更源自 exp4 三把刀（详见 [`../../exp4-core-function/PLAN.md`](../../exp4-core-function/PLAN.md) §2/§4）：**策略 ⟂ 状态**（π 不变、情景是输入）、**描述性 vs 规范性**（要不要她本人才算得出）、**两道墙**（端=需求可推导性 / 法=姿态许可）。

## 卡型（v2：废 `spine`，按"是 π 还是输入"分）

| type | 是什么 | 进哪个投影 |
|---|---|---|
| `core` | **不变策略 π，常驻**。违反即 OOC（want/need/wound/lie、姿态禁令、信任响应规则、关系姿态基线）。 | Decision（eval+prod） |
| `trigger` | **π 的条件分支**：if-then 触发卡。分支本身是 π；触发条件是输入。 | Decision（eval+prod） |
| `scene-axis` | **情景输入轴声明**（描述性）：trust / 在场 / 压强 / 关系。从场景读出、喂给 π、不定义角色；任何旁观者可读出（刀②），任意取值合法、被约束的是响应。 | Decision（eval+prod，作"输入轴"段） |
| `substrate` | 角色本体实例（皮肉） | 仅 prod |
| `voice` | 语气轨（皮肉） | 仅 prod |

**目的不立卡、不立轴**：它是 `core(情景)` 的运行时派生输出（规范性，必须过她的函数才有），由 core 卡 `derives` 声明，不得作 scene-axis。

## frontmatter 字段

| 字段 | 必填 | 进 Runtime | 含义 |
|---|---|---|---|
| `id` | ✓ | ✓(作 anchor) | kebab-case 唯一键 |
| `label` | ✓ | ✓(作标题) | 人读名，**只索引、不发令** |
| `type` | ✓ | 见投影纪律 | 上表五型 |
| `trigger` | trigger 必填 | ✓ | 触发谓词，**写在接地原语轴上**：`对象 / 在场结构 / 信任态 / 情绪压强 / 关系期待 / 话题` |
| `reads` | — | ✗不渲染 | 本卡读取哪些输入轴（取代 v1 `modulated_by`：从"被 X 调制"正名为"读取输入 X"）。**只许列 scene-axis 卡 id 或已 `derives` 声明的派生变量**——`check.py` lint 无悬空引用。耦合靠链接，不靠复制 |
| `derives` | — | ✗不渲染 | core 卡声明其运行时派生输出（如 `[目的]`），供 reads 引用与 lint |
| `overrides` | — | ✗不渲染 | 本卡覆盖哪些卡（如危难压过日常漏-夺回） |
| `status` | ✓ | **过滤**(仅 promoted 进) | `promoted` / `pending` |
| `anchors` | promoted 必填* | ✗剥 | 原文 uid 锚（铁律4）。*scene-axis 免锚（轴声明是架构而非机制断言） |
| `source` | ✓ | ✗剥 | 来源人判，如 `item09→v2.1` |

**v1 勘误**：`modulated_by` 旧文档写"渲染为'受…调制'"——`compile.py` 实际从不渲染（避免 kebab id 泄漏给 agent）。v2 的 `reads`/`derives`/`overrides` 同样**纯编写期元数据，不渲染**。

## 编号键（证据链与探针预登记的引用前提，exp4）

- **端的生成元**：`core` 卡定义里的常驻需求编号 **N1…Nk**（如 N1=被当作她自己看见）。
- **法的生成元**：`output-bans` 的姿态约束编号 **P1…Pk**。
- 编号**只是稳定引用键**（链引"哪条需求/哪条约束"用），不改语义、不新增机制；改号=破坏既有链引用，禁随意重编。

## 正文段（`## 段名`）

- **进 Runtime**：`内部判断`、`外显策略`、`禁止`、`定义`、`调制`、`目的` 等——即除下面外的所有段。
- **Atlas-only（编译剥掉）**：`例子`、`笔记`、`出处说明`。

## 卡边界判据（拆 / 合）

**前提**：当前所有卡**打包进 context 整体发给 agent**，无检索/RAG、无单卡隔离。→ **卡边界是编写/维护问题，不是 runtime 问题。** 不为"隔离/整洁"而拆。

只看两条：
1. **字段是否真分叉**：`trigger` 不同 **或** `外显策略` 不同 → 拆；触发与策略都一样 → 合。
2. **生命周期 / 修改频率**：会被**独立修改 / 不同节奏迭代** → 拆；总是一起动 → 合。

v2 的 trust 拆两半即此判据的应用：**轴声明**（scene-axis，描述轴，几乎不改）与**响应规则**（core，π，随人判迭代）生命周期不同 → 拆。

## 晋升闸

`status: pending → promoted` 的条件，按型：
- `trigger`：`(触发 + 内部判断 + 外显策略 + 禁止)` 四栏填满 **且** 过一次 rollforward 盲判。
- `core`：`定义 + 禁止` 两栏。
- `scene-axis`：仅 `定义`（**不进 OOC 四栏闸**——轴是输入声明，无所谓违反）。

**锚的现实**：部分卡源自 exp1 skill 定型前的早期工作，锚一时补不齐。这类记 `anchors: []` + `## 笔记` 注明"锚待补"，**仍可 promoted**。[`check.py`](../check.py) 把"promoted 但缺锚/缺栏"列为 **lint 警告（不阻断）**。

## 投影纪律（评测态剥离 / 生产态合并）

**核心原则：剥离是编译模式，不是对源的一次性 sweep。** 本体论是 core.wound→lie 的根、**留在真源剥不得**；它作 `type: substrate` 一等层活在 Atlas，由 `compile.py --mode` 决定进不进投影。同一 Atlas 出两个投影：

| 模式 | 进投影的层 | 用途 |
|---|---|---|
| `--mode eval`（默认） | scene-axis + core + trigger | **去名词留结构**：验决策机制 substrate-independent（反 recall 评测的公平投影） |
| `--mode prod` | Substrate + Decision + Voice 分层合并 | **披回皮肉但保持源码分层** |

Decision 渲染顺序：**输入轴（scene-axis）→ 常驻策略（core）→ 情景触发（trigger）**——先告诉 agent 读什么，再告诉它怎么响应。

**身份只活在 Substrate/Voice 层**——Decision 卡正文一律**本体无关**：
1. **纯记忆**（专名）→ 决策卡里写**角色槽**，具体实例由 substrate `## 槽绑定`。
2. **本体身份** → 决策卡里写**抽象形状**，具体实例由 substrate。
3. **行为机制** → 本就身份无关。
`check.py` 反 recall lint 扫每张决策卡的会编译段，内联专名/体征专名/语癖即告警。

## 不变量（违反即重蹈 exp1/exp2 覆辙；v2 增 5–6）

1. **trust 等输入轴是 scene-axis、用 `reads` 链接**，绝不复制进每张卡（保留压缩，防组合爆炸 + 切断耦合）。
2. **触发写在接地原语轴上**，不枚举具体情景（压缩不枚举，卡是基向量不是点）。
3. **Runtime 不编码散文规则**（留白/节奏/show-don't-tell）——那是语气轨。
4. **身份只活在 substrate/voice 层，决策卡正文本体无关**。
5. **π 与输入不混卡**（刀①）：core/trigger 里不存输入状态值，scene-axis 里不写响应规则——"参数"与"参数上的函数"分离。
6. **目的不入轴**（刀②）：规范性输出只能 `derives` 声明，不得立 scene-axis、不得进 reads 之外的任何输入位；推不出常驻需求的目的不认领（veto，端的墙）。
