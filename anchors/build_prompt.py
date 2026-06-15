#!/usr/bin/env python3
"""组装「逐卷锚点生成（单臂）」提示词。

输入只有两个核心参数：
  --volume / -v   卷号（决定读哪卷正文：canon/maintext/卷NN.json，经 canon_slice 切片）
  --out-dir / -o  输出目录（该臂锚点文件写到哪；Claude 臂→extract/claude/，Codex/GPT 臂→extract/codex/）

把填好的提示词打到 stdout，直接喂给一个模型臂即可。提示词正文是单一事实源——
要改提示词就改本脚本里的 GENERATE_TEMPLATE，别再在别处复制一份（见 PROMPT_锚点生成.md 维护纪律）。
"""

from __future__ import annotations

import argparse
import sys

# 两臂默认输出目录（--arm 的便捷映射；--out-dir 显式给则覆盖）
ARM_OUT_DIRS = {
    "claude": "anchors/extract/claude/",
    "codex": "anchors/extract/codex/",
}

ARM_EXTRA_INSTRUCTIONS = {
    "claude": "",
    "codex": "\nCodex 臂补充要求：范围留痕只需说明主轴 scene、只读梗概段和切分理由，**不必列出使用过的切片命令**。\n",
}

# 提示词正文。{{卷号}} 与 {{输出目录}} 由脚本替换；<id>/<起>/<止>/<短标题> 是留给模型填的占位符，保持原样。
GENERATE_TEMPLATE = """你的任务：为《狼与辛香料》正典**卷{{卷号}}**写一则逐场锚点记录，输出到 `{{输出目录}}`。工作目录是仓库根 `C:\\Users\\horo8\\project\\gold-annotation`。

### 这是什么活

项目在为赫萝（Holo）角色扮演系统冷启动**关系机制**。锚点记录＝读正典原文时留下的逐场笔记，是机制工作的**入口**：从原文里提取"她从哪出发 → 如何思考 → 落在行动"这条生成过程。它**不是机制结论**——不允许把单卷锚点写成 Policy/规则，只产出观察、暂时读法、候选弱模式。

### 第一步：吃透纪律与范例

先读这几样（范例是**参照**不是**模具**——范围怎么切、结构怎么摆，按本卷自己的判断来，别照抄旧骨架）：
1. `anchors/README.md` —— 生成流程、文件要求、弱约束、目录布局。
2. 一到两则现有锚点找手感，例如 `anchors/notebook/锚_卷03_s03-35_约伊兹隐瞒与阿玛蒂对决.md`。注意它分清了「事实观察 / 暂时读法 / 暂存弱模式」三层。
3. 如果你的锚点要接 DESIGN 概念（见输出结构第 6、7 节），读 `架构笔记.md` 的场景五元组与关系三字段——**只为读懂口径，不为给机制下定论**。

### 第二步：通读全卷（一步生成，不预选范围）

用切片脚本读原文。**务必带 `--canon-dir canon/maintext`，否则脚本默认路径有 bug。**

- 看 scene 目录：`python canon/tools/canon_slice.py -v {{卷号}} --list-scenes --canon-dir canon/maintext`
- 读某 scene 全文：`python canon/tools/canon_slice.py -v {{卷号}} -s <id> --number --canon-dir canon/maintext`（`--number` 给行号便于回指与亲核；`-b <起>` `-n <行数>` 可只取片段；`--join` 压缩换行）

在**一步内**完成「选范围 + 精读 + 写锚点」：

- **选范围是一等判断，不预选、不抹平。** 主轴 scene（真正承载关系张力的）逐句精读；物流/商战/过场一句梗概带过。这一卷可能没有连续大弧——若关系线是散点/被外部情节盖住的暗线，就如实切成散点，不要硬套大弧框架；若关系动作集中在某个小窗口，就深挖那个窗口，别为了覆盖面摊薄。范围怎么切本身要被对比，别提前替对比抹平。
- **退化条款**：仅当本卷长到一步通读不可靠（中段开始漏情节）时，先列一个客观分幕目录（只摘 scene、不判"算不算关系锚"），再回头精读选中的主轴。

### 第三步：写锚点文件

输出路径：`{{输出目录}}锚_卷{{卷号}}_s<起>-<止>_<短标题>.md`（文件名含卷、scene 范围、短标题）。

**推荐骨架（按本卷裁量增删，但 1–5 节是底线，6–8 节强烈鼓励）：**

1. **标题 + 范围留痕**（一等输出）：显式标注主轴 scene、哪些段只读梗概、**为什么这么切**，并能回指 `canon/maintext/卷{{卷号}}.json` 的 scene 范围。范围决策不进黑箱。{{臂额外要求}}
2. **本段之前已经在场的东西**：前史与关系档位，缺了它就看不懂本卷动作。把前几卷的旧伤/线索带进来（如"孤独会要人命""别替我安排退场""直接把真心话说出来""把我看得够重"）。
3. **这几幕直接发生了什么**：事实层。**每个关键动作都回指 scene + 行号**，引用原文保持短摘。
4. **值得盯住的细节**：本卷特有的别扭、不对称、与前几卷同核异形的地方。
5. **暂时并存的读法**：允许多解并存，只呈现解释路径，不裁决哪个是本质。
6. **（强烈鼓励，可选）与 DESIGN 的接口**：把本卷场景按场景五元组 / 关系三字段（关系位置 / trust 档 / 关系内压强）锚一下，方便下游机制工作定位。**明确声明这是分析锚定，不等于 active 圣经字段，也不构成字段准入主张**——字段化与准入归人审（`架构笔记.md` §0 gate，防 intimacy/conflict residue 回潮）。
7. **（强烈鼓励，可选）候选弱模式 + 支持场景/反例/待验证**：如果看出一条可迁移的生成过程苗头，写成候选弱模式，并配上它**支持的场景**与**会失效的反例方向**。**整节必须标"临时、带条件、非定稿"**，是给人审的候选，不是结论。
8. **现在不要急着抽象成什么**：诚实列出本卷抹平了就失真的几处别扭，提醒下游别把它压成干净结论。

### 三层纪律（贯穿全文）

- **事实观察 / 暂时读法 / 暂存弱模式** 三层必须分清且分别标注。读者要能一眼看出哪句是原文确实发生的、哪句是你的解释、哪句是你押的弱注。
- 事实层一律回原文亲核，带 scene + 行号短摘。
- 弱模式/候选抽象一律标"临时、带条件、非定稿"。

### 红线

- **不写 Policy、不下机制定论**——最高只到"候选弱模式"。
- **不把"像不像原文"当目标**：提取的是生成过程，不是表层模仿；贴近正典的表层只作警报与锚点。
- **scene 编号必须与 canon 对齐——逐一亲核！**（上一轮出过把 scene01 内容标成 scene04 的错置硬伤。写完回原文核一遍每个 scene 号。）
- **不回写 `canon/` 快照，不改任何已有文件**，只在 `{{输出目录}}` 下新建本卷锚点文件。

### 完成后回报（不用贴全文）

1. 最终选的主轴 scene 范围 + 切分理由（一句话）；
2. 本卷关系主线一句话概括；
3. 文件路径。
"""


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def parse_volume(value: str) -> str:
    """把 4 / 04 / 卷4 / 卷04 / 卷04.json 统一成两位数字串 '04'。"""
    raw = value.strip()
    if raw.endswith(".json"):
        raw = raw[:-5]
    if raw.startswith("卷"):
        raw = raw[1:]
    if not raw.isdigit():
        raise argparse.ArgumentTypeError("卷号须为数字、卷N 或 卷NN.json")
    number = int(raw)
    if not 1 <= number <= 11:
        raise argparse.ArgumentTypeError("卷号须在 1–11（当前正典快照只有 11 卷）")
    return f"{number:02d}"


def normalize_out_dir(value: str) -> str:
    """统一成正斜杠且以 / 结尾，便于和文件名直接拼接。"""
    out = value.strip().replace("\\", "/")
    if not out.endswith("/"):
        out += "/"
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="组装单臂逐卷锚点生成提示词，打到 stdout。",
    )
    parser.add_argument(
        "-v", "--volume", type=parse_volume, required=True,
        help="卷号：4 / 04 / 卷04 / 卷04.json 均可",
    )
    parser.add_argument(
        "-o", "--out-dir", type=normalize_out_dir, default=None,
        help="输出目录；不填则按 --arm 取默认（默认 claude 臂）",
    )
    parser.add_argument(
        "--arm", choices=sorted(ARM_OUT_DIRS), default="claude",
        help="模型臂，仅用于在未指定 --out-dir 时决定默认输出目录（默认 claude）",
    )
    return parser.parse_args()


def build_prompt(volume: str, out_dir: str, arm: str) -> str:
    return (
        GENERATE_TEMPLATE
        .replace("{{卷号}}", volume)
        .replace("{{输出目录}}", out_dir)
        .replace("{{臂额外要求}}", ARM_EXTRA_INSTRUCTIONS[arm])
    )


def main() -> int:
    configure_stdout()
    args = parse_args()
    out_dir = args.out_dir if args.out_dir is not None else ARM_OUT_DIRS[args.arm]
    sys.stdout.write(build_prompt(args.volume, out_dir, args.arm))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
