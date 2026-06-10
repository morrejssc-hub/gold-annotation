#!/usr/bin/env python3
"""晋升闸 lint（exp3 起，exp4 v2 适配）。

对每张 promoted 卡校验栏目齐 + 锚在不在，**默认 lint 警告不阻断**（--strict 才非零退出）。
- trigger 卡四栏 = frontmatter `trigger` + 正文 `内部判断/外显策略/禁止`
- core 卡两栏 = 正文 `定义 + 禁止`
- scene-axis 仅 `定义`（轴是输入声明，不进 OOC 四栏闸；免锚 lint）
- reads/derives 引用 lint：reads 的每个目标 ∈（scene-axis 卡 id ∪ 全 Atlas 已声明 derives），无悬空引用
- kebab id 泄漏 lint：会编译段里出现 kebab-case 研究术语即告警
- 缺锚 = `anchors` 空 → 提示"锚待补"
pending 卡只列出（在待验证池、本就不进 Runtime）。

用法: python3 check.py [--atlas atlas] [--strict]
"""
import argparse, re, sys
from pathlib import Path
import yaml

REQUIRED = {
    "trigger":    [("fm", "trigger"), ("sec", "内部判断"), ("sec", "外显策略"), ("sec", "禁止")],
    "core":       [("sec", "定义"), ("sec", "禁止")],
    "scene-axis": [("sec", "定义")],
}
# substrate/voice 是「实例/皮肉」层、非决策机制，不走栏目晋升闸。
DECISION_TYPES = {"core", "scene-axis", "trigger"}
KEBAB_RE = re.compile(r"\b[a-z]+(?:-[a-z]+)+\b")

# 反 recall 守卫：Decision 卡的「会进 Runtime 的正文段」不得内联本体专名 / 体征专名 /
# 语癖字——身份只能活在 substrate/voice 层。这是把 capstone（白领上司测试）的手工反 recall
# 自动化：每张决策卡都被检查 substrate-independent，而非每次手搓一个现代版场景。
COMPILED_SECTIONS = {"定义", "内部判断", "外显策略", "禁止", "调制"}
LEAK_TERMS = ["赫萝", "罗伦斯", "约伊兹", "丰收神", "狼神", "贤狼",
              "耳朵", "尾巴", "兽耳", "狼尾", "咱", "汝"]


def load(path):
    text = path.read_text(encoding="utf-8")
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm) or {}
    secs = set()
    cur, sec_text = None, {}
    for line in body.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            secs.add(cur)
            sec_text[cur] = []
        elif cur is not None:
            sec_text[cur].append(line)
    sec_text = {k: "\n".join(v) for k, v in sec_text.items()}
    return meta, secs, sec_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas", default="atlas")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    root = Path(__file__).parent
    cards = [(p, *load(p)) for p in sorted((root / a.atlas).rglob("*.md"))
             if p.name != "SCHEMA.md"]

    # reads/derives 引用域：scene-axis 卡 id ∪ 全 Atlas 已声明的派生变量。
    axis_ids = {m.get("id", p.stem) for p, m, _, _ in cards if m.get("type") == "scene-axis"}
    derived = {d for _, m, _, _ in cards for d in (m.get("derives") or [])}

    warns, leaks, anchor_todo, pend = [], [], [], []
    for p, meta, secs, sec_text in cards:
        sid = meta.get("id", p.stem)
        if meta.get("status") != "promoted":
            pend.append(sid)
            continue
        typ = meta.get("type", "trigger")
        if typ == "spine":
            warns.append(f"  ✗ {sid}: 过时 type: spine（v2 已废，应 re-type 为 core/scene-axis）")
            continue
        if meta.get("modulated_by") is not None:
            warns.append(f"  ✗ {sid}: 过时字段 modulated_by（v2 改名 reads）")
        for tgt in meta.get("reads") or []:
            if tgt not in axis_ids | derived:
                warns.append(f"  ✗ {sid}: reads 悬空引用「{tgt}」"
                             f"（须是 scene-axis 卡 id 或已 derives 声明的派生变量）")
        if typ in DECISION_TYPES:
            for kind, key in REQUIRED.get(typ, REQUIRED["trigger"]):
                ok = (key in meta) if kind == "fm" else (key in secs)
                if not ok:
                    warns.append(f"  ✗ {sid}: 缺 {'字段' if kind=='fm' else '段'} 「{key}」")
            # 反 recall：决策卡的会编译段不得内联身份/语癖（身份归 substrate/voice）；
            # kebab id 是研究术语，同样不得泄漏进会编译段。
            for sec in COMPILED_SECTIONS & secs:
                hit = sorted({t for t in LEAK_TERMS if t in sec_text.get(sec, "")})
                if hit:
                    leaks.append(f"  ✗ {sid}「{sec}」泄漏身份/语癖：{', '.join(hit)}")
                keb = sorted(set(KEBAB_RE.findall(sec_text.get(sec, ""))))
                if keb:
                    leaks.append(f"  ✗ {sid}「{sec}」泄漏 kebab 研究术语：{', '.join(keb)}")
        # scene-axis 免锚（轴声明是架构而非机制断言，见 SCHEMA v2）。
        if typ != "scene-axis" and not meta.get("anchors"):
            anchor_todo.append(sid)

    n = len([c for c in cards if c[1].get("status") == "promoted"])
    print(f"晋升闸 lint：{n} 张 promoted / {len(pend)} 张 pending")
    if warns:
        print("⚠ 四栏缺失（应修，或降回 pending）：")
        print("\n".join(warns))
    else:
        print("✓ 所有 promoted 决策卡四栏齐")
    if leaks:
        print("⚠ 反 recall：决策卡正文内联身份/语癖（应移入 substrate/voice 层）：")
        print("\n".join(leaks))
    else:
        print("✓ 决策卡正文无身份/语癖泄漏（substrate-independent）")
    if anchor_todo:
        print(f"○ 锚待补（不阻断）：{', '.join(anchor_todo)}")
    if pend:
        print(f"· 待验证池（不进 Runtime）：{', '.join(pend)}")

    if a.strict and (warns or leaks):
        sys.exit(1)


if __name__ == "__main__":
    main()
