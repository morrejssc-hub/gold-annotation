# PROMPT · 逐卷锚点生成（单臂用）

逐卷锚点生成的提示词已脚本化：`build_prompt.py`。提示词正文是**单一事实源**，就放在该脚本的 `GENERATE_TEMPLATE` 里——要改提示词改那里，别在别处复制第二份。

## 用法

只有两个核心参数：

| 参数 | 含义 |
|---|---|
| `-v` / `--volume` | 卷号（决定读哪卷正文 `canon/maintext/卷NN.json`，经 `canon_slice.py` 切片）。`4` / `04` / `卷04` / `卷04.json` 都认。 |
| `-o` / `--out-dir` | 输出目录（该臂锚点写到哪）。不填则按 `--arm` 取默认。 |
| `--arm` | `claude`（默认，→`anchors/extract/claude/`）或 `codex`（→`anchors/extract/codex/`）；仅在未给 `--out-dir` 时决定默认目录。 |

脚本把填好的提示词打到 stdout，直接喂给一个模型臂：

```bash
# Claude 臂写卷05（默认输出 anchors/extract/claude/）
python anchors/build_prompt.py -v 5

# Codex/GPT 臂写卷05
python anchors/build_prompt.py -v 5 --arm codex

# 显式指定输出目录
python anchors/build_prompt.py -v 5 -o anchors/extract/codex/
```

## 流程位置

- **两臂各喂一份、独立产出、不共享中间结果**（见 `README.md` 生成流程第 1 步）。不得用 subagent 顶替另一真模型臂（同源会制造"已交叉验证"的假象）。Claude 臂走 Claude Code subagent，Codex/GPT 臂是外部真模型。
- 两臂都产出后，走 `README.md` 第 4 步（对比 + 生发新想法——并排列三类分歧，**并交付两版并置才浮出的新读法／新落点**，不只是机械差异清单；纪律是不给两臂排名、不替人拍板。输出到 `anchors/extract/对比_卷NN_臂A-vs-臂B.md`）与第 5 步（人审定稿，裁决 + 综合，合并稿落 `notebook/`）。

## 维护纪律

每次跑完发现提示词的缺口（如某次出了 scene 编号错置硬伤），把教训补回 `build_prompt.py` 的 `GENERATE_TEMPLATE`，别让同一个坑踩第二次。这份模板的修订史就是踩坑史。
