#!/usr/bin/env python3
"""Atlas → Runtime 单向编译器（exp3）。

Atlas 卡片 = YAML frontmatter + `## 段名` 正文。本脚本：
  - 只收 status: promoted 的卡（pending 留待验证池，不进 Runtime）；
  - 剥掉 Atlas-only：frontmatter 的 anchors/source/status + 正文的 例子/笔记/出处说明；
  - 脊柱（spine）先排，触发卡（trigger）后排；
  - modulated_by 渲染成"受 X 调制"，trigger 谓词紧凑成一行。
单一真源 → 编译，故 Atlas↔Runtime 不可能 desync（不手维两份）。

用法: python3 compile.py [--atlas atlas] [--out runtime.md]
"""
import argparse, sys
from pathlib import Path
import yaml

ATLAS_ONLY_SECTIONS = {"例子", "笔记", "出处说明"}
DROP_FIELDS = {"anchors", "source", "status", "id", "type"}


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
    # modulated_by / overrides 只是编写期耦合元数据（防复制、记关系），
    # 不渲染进 Runtime：①避免 kebab id 作研究术语泄漏给 agent；
    # ②耦合/覆盖关系本就写在卡体里（trust 常驻、危难卡自述覆盖）。check.py 仍读这些字段。
    out = [f"## {meta['label']}"]
    trig = meta.get("trigger")
    if trig:
        out.append("**触发**：" + "；".join(f"{k}={v}" for k, v in trig.items()))
    for name, content in sections.items():
        if name in ATLAS_ONLY_SECTIONS or not content:
            continue
        out.append(f"**{name}**：\n{content}")
    return "\n\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas", default="atlas")
    ap.add_argument("--out", default="runtime.md")
    a = ap.parse_args()
    root = Path(__file__).parent
    cards = [parse_card(p) for p in sorted((root / a.atlas).rglob("*.md"))
             if p.name != "SCHEMA.md"]

    promoted = [(m, s) for m, s, _ in cards if m.get("status") == "promoted"]
    pending = [p for m, s, p in cards if m.get("status") != "promoted"]
    spine = [(m, s) for m, s in promoted if m.get("type") == "spine"]
    trig = [(m, s) for m, s in promoted if m.get("type") != "spine"]

    parts = ["# 生成机制（角色回应的内部规则；勿手改——改 atlas/）\n",
             "> 单向编译产物：`python3 compile.py`。\n",
             "## 常驻（始终生效）\n"]
    parts += [render(m, s) for m, s in spine]
    parts.append("\n## 情景触发（命中条件才取）\n")
    parts += [render(m, s) for m, s in trig]

    (root / a.out).write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"✓ 编译 {len(promoted)} 张已晋升卡 → {a.out}"
          f"（脊柱 {len(spine)} / 触发 {len(trig)}）")
    if pending:
        print(f"  待验证池（未进 Runtime）：{', '.join(p.stem for p in pending)}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
