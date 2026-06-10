# exp3 · Atlas/Runtime 拆分 + 机制卡片标准化

> 续 [exp1](../exp1-bible-vs-naked/FINDINGS.md)（决策圣经闭环）+ [exp2](../exp2-probe/FINDINGS.md)（决策不下沉权重、trust 是接地构件的**派生读数**不是原语）。
> **这不是可证伪实验，是 refactor**——把 exp1 的单体 `bible_v1.md`(实为 v2.2) 拆成 **Atlas(真源) → 编译 → Runtime(投影)**，并把散文机制抽成**标准字段卡片**。
> 时间锚：2026-06-09。主导：Claude；人审/资源：用户。

## 0. 成功判据（refactor 不靠"更整齐"，靠回归不退化）

**编译出的 Runtime，在 held-out item 上重跑，盲判胜率 ≥ 单体 `bible_v2.2`，且 Atlas↔Runtime 零 desync（单向编译、绝不手维两份）。**

挂这道回归闸，是把纯文档活动焊回 exp1 的实证闭环——拆完若行为退化，schema 就是错的。

## 1. 拆成什么

- **Atlas**（真源 / 含待验证池）：卡片**全字段** + 例子 + 原文锚 uid + 来源 item + 晋升状态。
- **Runtime**（投影）：编译产物，**剥**例子/锚/来源/未晋升卡，只留 `label + 触发 + 内部判断 + 外显策略 + 禁止`。克制、状态机化。
- **素材**：`../exp1-bible-vs-naked/items/`、`voice_gold/`、脚本——沿用 exp1，不动。
- **晋升闸**：一条机制 `(触发 + 内部判断 + 外显策略 + 禁止)` 四栏填满 **且** 过一次 rollforward 盲判，`status` 才从 `pending → promoted`、进 Runtime；半退不退留待验证池。

## 2. 字段标准（从 bible_v2.2 抽，不发明）

见 [`atlas/SCHEMA.md`](atlas/SCHEMA.md)。两类条目：
- **脊柱状态变量**（trust 轴、§0 禁令）：常驻、`modulate` 别的卡，**不是 if-then**。
- **触发卡**（§5 if-then）：`trigger` 写在接地原语轴上 `{对象, 在场结构, 信任态, 情绪压强, 关系期待}`。

**硬约束（exp2 教训）**：trust 是脊柱，用 `modulated_by` **链接**到它管的卡，**绝不复制进每张卡**——复制 = 组合爆炸 + 切断 exp1 v2.0 的"一根轴塌两维"耦合。**字段层面保留压缩**，就是 exp2 那条认识论教训的落地。

## 3. 本轮纵切（先证最硬的格子，不铺全量）

`trust` 脊柱 + 它调制的**两张卡**：
- `leak-then-reclaim`（藏不藏侧：漏一句近直白 → 封顶 → 倒打一耙夺回主动权）
- `authority-relax`（主动权侧：随信任放松、示弱即攻）

这正是 exp1 v2.0 统一的"一根轴塌两维"——**1 个脊柱变量 → 2 张卡**。schema 在最硬处先证能保住压缩，再扩全量。先铺全量 = schema 没经测试就过度设计。

- **回归靶**：`item09`（卷4 高信任日常脆弱，正好打 §5b/§6 trust 漏口）。
- **协议**：把 `bible_v2.2` 的 §5b/§6 区域换成"编译产物"、其余 verbatim → 圣经臂重跑 item09 → **人审盲判是否 ≥ 原版**。fielding 只该丢锚/例子，**不该丢决策内容**；若丢了，人审会看见。

## 4. rollforward 来源（分用途，沿 exp1 铁律 5/7 + exp2）

| 用途 | 来源 |
|---|---|
| 机制锚定（铁律4，每条挂 uid） | **正文/番外，不可替代** |
| held-out 标准对照组 | 正文，`rollforward.py` 切 |
| 晋升判官战场 / 发现新卡 | **非正典自拟 + 多轮**（正文单轮是废裁判，铁律5） |
| 触发轴里正文焊死覆盖不到的格子（如高信任×第三方在场） | **改写造**（exp2：语料焊死，正文无此组合） |

## 5. 进度

- [x] 目录 + SCHEMA + 纵切 4 卡（trust 脊柱 / §0 禁令 / leak-then-reclaim / authority-relax）
- [x] `compile.py` Atlas → runtime.md；修内联锚泄漏（锚归 `## 例子`，Runtime 已验无锚）
- [x] 圣经臂(hybrid 编译卡片)重跑 item09 → `regression/item09_result.md`，候选已出
- [x] **回归①** item09(trust 状态变量耦合)：人判"决策区分不明显"=未丢决策=PASS（偏好乙落语气轨）
- [x] **回归②** item05(§6b 时序闸=控制流)：两臂均命中时序闸=schema 兜得住控制流；逮到并修 fielding 漏"纠结即行动"；编译剥例子反而不 parrot 锚句
- [x] 扩全量 §1–§5/§7/§8 成卡（共 15 张：脊柱 5 / 触发 10），编译干净
- [x] 卡边界判据写进 SCHEMA（打包发 agent、无隔离 → 拆/合只看字段分叉 + 生命周期）
- [x] 晋升闸脚本化 `check.py`（四栏齐 + 锚 lint，不阻断；逮到并修了 2 张非规范段名）
- [x] 全量去身份 sweep：纯记忆专名剥成角色槽、本体（狼/皮草/被供奉）按"去标签保形状"留、研究 meta→笔记、例子→例子、de-bold；compiler 去术语/不渲染 kebab id；voice-boundary 降 pending
- [x] **Bob 测试**：伴侣→Bob、本体留，机制臂守纪律但用户判"本体+语癖仍露角色"
- [x] **白领上司测试（capstone）**：身体+语癖全换、wound 改职场版同 lie；机制臂被用户选中、裸臂藏过头+两清距离化 → 机制 substrate-independent（复现 exp2 R4，经编译圣经）
- [x] 长出机制：夺回有两种 botch（软下去 / 两清距离化）→ leak-then-reclaim 卡已补
- [x] **评测态/生产态双投影**（修去身份 sweep 把剥离做进了源、违反 Atlas-是最全真源的内伤）：本体复活为 `type: substrate` 一等层（`atlas/substrate/holo.md`，挂锚）；`compile.py --mode eval|prod`——eval 只发 Decision（去名词留结构、反 recall 公平投影）、prod 分层合并 Substrate+Decision+Voice；修两处泄漏（output-bans 耳尾→体征通道、unworthy-opponent 汝→例子）；`check.py` 加反 recall lint（决策卡正文内联身份/语癖即告警 = capstone 自动化）。eval 投影 vs 旧 runtime.md 仅差两处 leak-fix → **机械证决策无损**（盲判半待人审）。删停产的单 runtime.md 防 desync。
- [ ] 收尾①：voice 正面腔提示 + voice_gold few-shot 重构成 `type: voice` 卡，填上 prod 投影的「三、语气轨」空层（prompt 现态→LoRA 后续）
- [ ] 收尾②：prod 四层装配的「披全身份后机制仍点火」生产态盲判（对冲 legible=cosplay 回潮风险，Bob 测试已显本体一在模型就靠 recall）——**待真要发生成 artifact 或上第二角色再做**，不为单角色提前浇筑
- [ ] 收尾③：全项目目录整理（清理根下旧 units 杂物），再 promote 出 experiments/ 成生产圣经
