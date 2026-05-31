# 归属评测集 · 起步套件

把"标注"从**逐条输入**变成**逐条确认**：机器先预填一个 guess，你只核对、只改错的那几行。

## 文件

| 文件 | 作用 |
|---|---|
| `aliases.json` | 别名表（实体登记表）。canonical→所有称呼/绰号。**只放专名，不放代词。**每卷音译差异要校对。 |
| `prepare.py` | 一章 json → `sheet.tsv`（待核对表）。抽对话/动作/无主语FID单元，预填 guess+置信度+难度桶+focalizer+target+上下文。 |
| `pool.py` | 把**多篇** json 一次抽成大候选池 `pool.tsv`（带 `source` 列），并体检每篇别名命中率。 |
| `sample.py` | 从池子取样：`--mode eval` 分层+跨篇铺开建评测集；`--mode sft` 高置信建训练种子。 |
| `merge.py` | 改了抽取器想重跑，但不想毁掉已核对的行 → 把新表增量并进旧表，保人工列。 |
| `health.py` | **建 gold 阶段**的进度体检：各桶标到哪、还差多少、优先核对队列。（不是评分） |
| `score.py` | **评测阶段**：核对完的 tsv → 按桶准确率 + 置信度校准曲线 + 结构性体检（评的是 guess 列那个系统）。 |

> 表格软件会把 `1-0` 自动存成日期（`Jan-00`）。所以 `uid` 用下划线 `1_0`，且 `merge`/`score` 都按
> `scene`/`sent` 列对齐，不依赖 uid——就算 uid 被存坏也不影响。一句拆多个单元用后缀 `1_8a`/`1_8b`。

## 工作流

```bash
# 1) 首次生成待核对表
python3 prepare.py ../sw-sft/jsons/狼与将晓之色.json > sheet.tsv

# 1') 改了抽取器后重跑, 不毁已核对的行: 生成新表再 merge
python3 prepare.py ../sw-sft/jsons/狼与将晓之色.json > new.tsv
python3 merge.py sheet.tsv new.tsv > merged.tsv   # 看一眼没问题再 mv merged.tsv sheet.tsv

# 2) 用表格软件打开 sheet.tsv（制表符分隔），逐行核对：
#    - 读 context 列（►标出的是当前句，‖ 分隔上下文）
#    - guess 错就改 gold_speaker；对就不动；focalizer 整场核一次
#    - 每核对一行，在 checked 列填 y（没填 y 的行不计分——杜绝"全盘照抄"刷假准确率）
#    - 约定：gold_speaker 填 canonical 名；不是角色台词(旁白/引用)填 —
#    - 这是初筛：低置信(conf≤0.4)的无主语行多半要么改归属、要么直接删（环境噪声）

# 3) 建集进度（标到哪了、哪个桶还差）
python3 health.py sheet.tsv

# 4) 有了 LLM 预测覆盖 guess 列后，才用 score 评测
python3 score.py sheet.tsv
```

## 列含义

列序: `uid scene sent type bucket focalizer context text guess_speaker guess_conf gold_speaker target checked note`

`guess_speaker` = **被评测的系统**的预测。`gold_speaker` = 你给的真值。
默认 guess 是启发式基线（很弱，见下）。**要评测你的 LLM prompt，就把 LLM 的预测写进 guess 列**（改 `prepare.py` 里 `--llm` 占位处，接 OpenAI 兼容接口），gold 列不变，再跑 score。

## bucket 列（score 按它分开统计，对话/动作各自成组）

对话行填**难度**，动作行填**类型**，两套值不重叠：

- 对话：`explicit` 显式（"罗伦斯说"）· `anaphoric` 回指/后指 · `unmarked` 无标签轮替
- 动作：`物理`（皱眉/转身/看着）· `心理-自指`（自己盘算/觉得——**思考方式，最值钱**）·
  `心理-推测`（视角角色揣度**别人**的心思，即 theory-of-mind；`target`填被推测者）

**focalizer 列**：视角角色（近距三人称里整场基本锁定一人，SW=罗伦斯）。无主语的内心/旁白
默认归 focalizer——这把"自由间接引语(FID)谁在想"的暧昧一次性消解。机器整场预填同一个值，你核对一次即可。

**心理-推测 的自动判定**只走"情态标记（似乎/大概/恐怕/听起来…）+ 别人作主语"这条高精度路径
（如"艾尔莎**大概**已体会过寂寥感"→ 罗伦斯在推测，target=艾尔莎）。**不**靠"句中另有人名"硬判，
以免把"罗伦斯叙述赫萝的状态"错标成推测。漏掉的你核对时手动提升即可（初筛，重精度不重召回）。

每桶 **≥30 条**数字才可信；目标 dev≈500 / test≈300，**跨 5~8 篇不同文风**采样。

## target 列（选填，不计入准确率）

"面对什么 / 对谁说"。属于**内容层(L2)**，不是归属层(L1)——边界模糊（看着"赫萝"还是
"赫萝饮酒"？），所以 score **只报填写率、不打分**。值得填的是**对话的 addressee**：
赫萝对罗伦斯说和对商人说语气不同，这一列能 condition 风格。

## 归属粒度规则（消除"标到哪"的纠结）

- 一句**同时是环境+动作**没关系：纯环境句 gold 填 `—` 丢掉；有角色动作的，环境部分当上下文搭车。
- 一句**多个施动者**（"罗伦斯看着赫萝饮酒"）：归**主句前景施动者**（罗伦斯）；嵌在感知/认知
  宾语里的动作（赫萝饮酒）算 target/内容，不单独归属。只有并列的独立主句动作分属不同人才拆，并标低置信。

## 覆盖度：跨短篇取样（建评测集的关键）

单章评测集测不出泛化。流程是 **池 → 分层取样 → 核对 → merge**：

```bash
# 0) 标视角角色(只做一次): 生成待填表, 人确认/补 focalizer 列, pool/prepare 自动读用
python3 focalizers.py > focalizers.tsv               # 第三人称已预填; 第一人称/异类留空待填
#    第一人称短篇(narr_我 高)的视角是叙述者"我", 名字未必在 aliases, 直接写角色名即可
python3 pool.py ../sw-sft/jsons/ > pool.tsv          # 自动按 focalizers.tsv 覆盖启发式
# 评测集: 质量优先, 跨篇铺开, 排除别名没覆盖的异类短篇, 跳过已核对的
python3 sample.py pool.tsv --require-focalizer \
  --drop-source "黑狼的摇篮,牧羊人与黑骑士,狼与彩虹色的音乐,狼与银色的叹息,狼与将晓之色" \
  --exclude sheet.tsv > eval_candidates.tsv
python3 merge.py sheet.tsv eval_candidates.tsv > merged.tsv   # 核对前后都能 merge
```

**取样按【质量】, 不按归属难度**：归属对错你我都会 check, 不是瓶颈; 评测集的价值在单元有没有"料"。
所以 `sample.py`:
1. **质量闸**(`--min-chars`, 默认 6)：砍掉 ≤5 字短对话、纯语气词(嗯/是吗)、琐碎短动作(点点头)。
2. **价值类配额**(`--quota "对话:110,心理:90,物理:40"`)：偏向声口(对话)与思考方式(心理), 压低物理。
3. 类内按**质量分**取(长度封顶 40 防偏长 + 心理加成), 跨 source 铺开。

**两种产物**：评测集用上面的质量优先;  **SFT 种子**(`--mode sft --min-conf 0.7`)同样过质量闸,
再按高置信筛——那才是"挑高置信、其余丢、抽样审计"。

**别名覆盖盲区**（`pool.py` 已自动体检并标 ⚠）：`黑狼的摇篮`/`牧羊人与黑骑士`/`狼与彩虹色的音乐`
等短篇主角不是罗伦斯/赫萝（艾普的过去、诺儿菈+艾尼克…），命中率低、focalizer 失准。要纳入这些文风，
先把它们的角色补进 `aliases.json` 再重跑 pool。当前评测集已用 `--drop-source` 把它们排除。

`幕间.json` 解析失败（坏 json），pool 已跳过——要它的话先修文件。

## 这套样例证明了什么

在 `狼与将晓之色` 第一章上，朴素"最近名字"启发式只有 **29%**——因为它把引号里提到的
`赫萝`当成说话人。真正的说话人要靠叙述线索（"罗伦斯自言自语"/"艾尔莎说出这番话"）做
**篇章级推断**，这不是分词/NER 能解的。`example.tsv` 是核对好的 17 个对话单元，可直接
`python3 score.py example.tsv` 复现。换上 LLM 预测，你就能量化它比 29% 好多少、好在哪个桶。

## 下一步接 LLM

`prepare.py --llm` 目前是占位。接入时：每条让模型在【在场角色候选 + 上下文窗口】里
**选一个**（受限输出），强制返回 `speaker / confidence / evidence`。然后：
1. 在本 gold 集上跑出 score → 看总分和分桶；
2. 看校准曲线把 `confidence` 翻译成真实可信度（如"conf≥0.9 实测 96%"）；
3. 用这个阈值去筛全量正文，只留高置信，抽样审计兜底。
