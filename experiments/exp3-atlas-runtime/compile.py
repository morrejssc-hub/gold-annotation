#!/usr/bin/env python3
"""Atlas → Runtime 单向编译器（exp3）。

Atlas 卡片 = YAML frontmatter + `## 段名` 正文。本脚本：
  - 只收 status: promoted 的卡（pending 留待验证池，不进 Runtime）；
  - 剥掉 Atlas-only：frontmatter 的 anchors/source/status + 正文的 例子/笔记/出处说明；
  - Decision 渲染顺序（v2）：输入轴（scene-axis）→ 常驻策略（core）→ 触发卡（trigger）；
  - reads/derives/overrides 纯编写期元数据，不渲染（防 kebab id 研究术语泄漏）。
单一真源 → 编译，故 Atlas↔Runtime 不可能 desync（不手维两份）。
v2（exp4 re-type）：废 `spine`，拆成 core（不变策略 π）/ scene-axis（情景输入轴）。

**两个投影目标（评测态剥离、生产态合并）**：
  --mode eval（默认）：只编译 Decision 层（spine + trigger），剥掉 substrate/voice 层。
      = 去名词留结构，验决策机制 substrate-independent（反 recall 评测的公平投影）。
      输出 runtime.eval.md。
  --mode prod：Substrate + Decision + Voice 分层合并（披回皮肉但保持源码分层）。
      输出 runtime.prod.md。
身份/语癖只活在 Substrate/Voice 层，决策卡正文一律本体无关——两投影同源、靠分层而非改卡。

用法: python3 compile.py [--mode eval|prod] [--atlas atlas] [--out PATH]
"""
import argparse, sys
from pathlib import Path
import yaml

ATLAS_ONLY_SECTIONS = {"例子", "笔记", "出处说明"}
# 层归类：Decision = 决策机制（两投影都进）；Substrate/Voice = 仅 prod 合并。
# v2：spine 已废——遇到即报错（应 re-type 为 core / scene-axis）。
DECISION_TYPES = {"core", "scene-axis", "trigger"}
SUBSTRATE_TYPES = {"substrate"}
VOICE_TYPES = {"voice"}


def parse_card(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path}: 缺 frontmatter")
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm) or {}
    sections = {}
    cur = None
    for line in body.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            sections[cur] = []
        elif cur is not None:
            sections[cur].append(line)
    sections = {k: "\n".join(v).strip() for k, v in sections.items()}
    return meta, sections, path


def render(meta, sections):
    # reads / derives / overrides 只是编写期耦合元数据（防复制、记关系），
    # 不渲染进 Runtime：①避免 kebab id 作研究术语泄漏给 agent；
    # ②耦合/覆盖关系本就写在卡体里（轴常驻、危难卡自述覆盖）。check.py 仍读这些字段。
    out = [f"## {meta['label']}"]
    trig = meta.get("trigger")
    if trig:
        out.append("**触发**：" + "；".join(f"{k}={v}" for k, v in trig.items()))
    for name, content in sections.items():
        if name in ATLAS_ONLY_SECTIONS or not content:
            continue
        out.append(f"**{name}**：\n{content}")
    return "\n\n".join(out)


def decision_block(promoted):
    axes = [(m, s) for m, s in promoted if m.get("type") == "scene-axis"]
    core = [(m, s) for m, s in promoted if m.get("type") == "core"]
    trig = [(m, s) for m, s in promoted if m.get("type", "trigger") == "trigger"]
    parts = ["## 情景输入轴（每场先从场景读出，喂给下面的策略）\n"]
    parts += [render(m, s) for m, s in axes]
    parts.append("\n## 常驻策略（始终生效）\n")
    parts += [render(m, s) for m, s in core]
    parts.append("\n## 情景触发（命中条件才取）\n")
    parts += [render(m, s) for m, s in trig]
    return parts, len(axes), len(core), len(trig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["eval", "prod"], default="eval")
    ap.add_argument("--atlas", default="atlas")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(__file__).parent
    cards = [parse_card(p) for p in sorted((root / a.atlas).rglob("*.md"))
             if p.name != "SCHEMA.md"]

    stale = [m.get("id", p.stem) for m, s, p in cards if m.get("type") == "spine"]
    if stale:
        sys.exit(f"✗ 过时 type: spine（v2 已废，应 re-type 为 core/scene-axis）：{', '.join(stale)}")

    promoted = [(m, s) for m, s, _ in cards if m.get("status") == "promoted"]
    pending = [p for m, s, p in cards if m.get("status") != "promoted"]
    decision = [(m, s) for m, s in promoted if m.get("type") in DECISION_TYPES]
    substrate = [(m, s) for m, s in promoted if m.get("type") in SUBSTRATE_TYPES]
    voice = [(m, s) for m, s in promoted if m.get("type") in VOICE_TYPES]

    out_path = a.out or (f"runtime.{a.mode}.md")
    dparts, n_axes, n_core, n_trig = decision_block(decision)

    if a.mode == "eval":
        # 评测态：去名词留结构——只发 Decision 层。
        parts = ["# 生成机制（角色回应的内部规则；勿手改——改 atlas/）\n",
                 "> 评测投影：`python3 compile.py --mode eval`。已剥本体/语癖，"
                 "只留决策机制的抽象生成规则（验 substrate-independent）。\n"]
        parts += dparts
    else:
        # 生产态：披回皮肉但保持源码分层——Substrate + Decision + Voice 并列。
        parts = ["# 角色生成圣经（生产态；勿手改——改 atlas/）\n",
                 "> 生产投影：`python3 compile.py --mode prod`。分层合并，非单体散文。\n",
                 "# 一、角色本体（Substrate）\n"]
        parts += [render(m, s) for m, s in substrate] or ["（无 substrate 卡）"]
        parts.append("\n# 二、决策机制（Decision Runtime）\n")
        parts += dparts
        parts.append("\n# 三、语气轨（Voice Runtime）\n")
        parts += ([render(m, s) for m, s in voice]
                  or ["（voice 层待重构成独立语气轨，见 PLAN 收尾①）"])

    (root / out_path).write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    tag = (f"输入轴 {n_axes} / 常驻 {n_core} / 触发 {n_trig}" if a.mode == "eval"
           else f"substrate {len(substrate)} / 决策 {len(decision)} / voice {len(voice)}")
    print(f"✓ [{a.mode}] 编译 → {out_path}（{tag}）")
    if pending:
        print(f"  待验证池（未进 Runtime）：{', '.join(p.stem for p in pending)}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
