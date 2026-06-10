#!/usr/bin/env python3
"""晋升闸 lint（exp3）。

对每张 promoted 卡校验四栏齐 + 锚在不在，**默认 lint 警告不阻断**（--strict 才非零退出）。
- trigger 卡四栏 = frontmatter `trigger` + 正文 `内部判断/外显策略/禁止`
- spine 卡四栏 = 正文 `定义 + 禁止`（状态变量另需 `调制`）
- 缺锚 = `anchors` 空 → 提示"锚待补"（多为 skill 定型前的早期卡，见 SCHEMA）
pending 卡只列出（在待验证池、本就不进 Runtime）。

用法: python3 check.py [--atlas atlas] [--strict]
"""
import argparse, sys
from pathlib import Path
import yaml

REQUIRED = {
    "trigger": [("fm", "trigger"), ("sec", "内部判断"), ("sec", "外显策略"), ("sec", "禁止")],
    "spine":   [("sec", "定义"), ("sec", "禁止")],
}


def load(path):
    text = path.read_text(encoding="utf-8")
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm) or {}
    secs = set()
    for line in body.splitlines():
        if line.startswith("## "):
            secs.add(line[3:].strip())
    return meta, secs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas", default="atlas")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    root = Path(__file__).parent
    cards = [(p, *load(p)) for p in sorted((root / a.atlas).rglob("*.md"))
             if p.name != "SCHEMA.md"]

    warns, anchor_todo, pend = [], [], []
    for p, meta, secs in cards:
        sid = meta.get("id", p.stem)
        if meta.get("status") != "promoted":
            pend.append(sid)
            continue
        typ = meta.get("type", "trigger")
        for kind, key in REQUIRED.get(typ, REQUIRED["trigger"]):
            ok = (key in meta) if kind == "fm" else (key in secs)
            if not ok:
                warns.append(f"  ✗ {sid}: 缺 {'字段' if kind=='fm' else '段'} 「{key}」")
        if typ == "spine" and meta.get("modulated_by") is None \
           and "调制" not in secs and sid == "trust":
            warns.append(f"  ✗ {sid}: 状态变量缺 「调制」段")
        if not meta.get("anchors"):
            anchor_todo.append(sid)

    n = len([c for c in cards if c[1].get("status") == "promoted"])
    print(f"晋升闸 lint：{n} 张 promoted / {len(pend)} 张 pending")
    if warns:
        print("⚠ 四栏缺失（应修，或降回 pending）：")
        print("\n".join(warns))
    else:
        print("✓ 所有 promoted 卡四栏齐")
    if anchor_todo:
        print(f"○ 锚待补（不阻断）：{', '.join(anchor_todo)}")
    if pend:
        print(f"· 待验证池（不进 Runtime）：{', '.join(pend)}")

    if a.strict and warns:
        sys.exit(1)


if __name__ == "__main__":
    main()
