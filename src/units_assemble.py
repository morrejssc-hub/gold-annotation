#!/usr/bin/env python3
"""
units_assemble.py —— 纯机械组装：从 units/<model>/<篇>.json 按句序抽出某角色的"流"，
切成"回合(turn)"，并渲染角色扮演样本 (上文场景 → 该角色本回合的 说+做)。无 AI 介入。

回合 = 该角色在章内连续(相邻 uid 位置)出现的极大段；中间隔着他没出现的句子即断回合。
角色扮演样本：input = 本场景从开头(或上一回合结束)到本回合前的全部句子(verbatim 上文)；
              target = 本回合里该角色 involved 的句子(verbatim，标 说/做)。

用法:
  python3 units_assemble.py units/claude/旅途余白.json --char 赫萝
  python3 units_assemble.py units/claude/旅途余白.json --char 赫萝 --scene 2 --samples 2
"""
import json, os, argparse

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root: 脚本在 src/, 数据在根


def scene_of(uid):
    return uid.split("_")[0]


def load_cast_entry(source, char):
    """返回该 char 的 cast 条目（找不到/无 cast 返回 None）。"""
    p = os.path.join(HERE, "casts", source + ".json")
    if not os.path.exists(p):
        return None
    cast = json.load(open(p, encoding="utf-8"))
    for c in cast.get("cast", []):
        if c["canonical"] == char or char in c.get("aka", []):
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("units"); ap.add_argument("--char", required=True)
    ap.add_argument("--scene", default=None, help="只看某 scene")
    ap.add_argument("--samples", type=int, default=0, help="渲染 N 个 (上文→回合) 样本")
    ap.add_argument("--keep-low", action="store_true",
                    help="保留 conf=low 的「做」（默认 target 侧丢弃，只留高质量回应）")
    args = ap.parse_args()

    d = json.load(open(args.units, encoding="utf-8"))
    U = d["units"]
    char = args.char

    # playable 门控：present:false 或 playable:false 的角色不组装角色扮演样本
    entry = load_cast_entry(d.get("source", ""), char)
    if entry is not None:
        if entry.get("present") is False:
            print(f"# ⚠ {char} present=false（本篇未当场登场，无场景内回应）→ 不可组装为角色扮演样本")
            return
        if entry.get("playable") is False:
            note = entry.get("playable_note", "群体/路人/背景，非可扮演角色")
            print(f"# ⚠ {char} playable=false（{note}）→ 不组装角色扮演样本")
            return

    # 该角色 involved 的句子位置 + role；target 侧默认丢弃 low-conf 的「做」（边缘/焦点者推断）
    dropped_low = 0
    mine = {}  # pos -> roles list
    for i, u in enumerate(U):
        roles = set()
        for x in u["involves"]:
            if x["char"] != char:
                continue
            if x["role"] == "做" and x.get("conf") == "low" and not args.keep_low:
                dropped_low += 1
                continue
            roles.add(x["role"])
        if roles:
            mine[i] = sorted(roles)

    # 切回合：相邻位置(差1)归一回合
    turns, cur = [], []
    for pos in sorted(mine):
        if cur and pos == cur[-1] + 1:
            cur.append(pos)
        else:
            if cur: turns.append(cur)
            cur = [pos]
    if cur: turns.append(cur)

    if args.scene:
        turns = [t for t in turns if scene_of(U[t[0]]["uid"]) == str(args.scene)]

    n_say = sum(1 for p in mine if "说" in mine[p])
    low_note = f"；已滤 low-conf 做 {dropped_low} 句" if (dropped_low and not args.keep_low) else (
        "；--keep-low 保留低 conf 做" if args.keep_low else "")
    print(f"# {char} @ {args.units}")
    print(f"# 出现句 {len(mine)}（含说 {n_say} / 做 {sum(1 for p in mine if '做' in mine[p])}）；回合 {len(turns)}"
          + (f"（scene {args.scene}）" if args.scene else "") + low_note)
    print()

    # 流视图（回合分段）
    for t in turns:
        uid0 = U[t[0]]["uid"]
        print(f"━━ 回合 {uid0}–{U[t[-1]]['uid']} ━━")
        for pos in t:
            u = U[pos]
            print(f"  {u['uid']}│{'/'.join(mine[pos])}│{u['text']}")
        print()

    # 角色扮演样本
    if args.samples:
        print("=" * 60)
        print(f"角色扮演样本（input=场景上文 / target={char}本回合）")
        shown = 0
        for t in turns:
            if shown >= args.samples: break
            sc = scene_of(U[t[0]]["uid"])
            # 本场景开头位置
            sc_start = next(i for i, u in enumerate(U) if scene_of(u["uid"]) == sc)
            ctx = U[sc_start:t[0]]
            print("\n" + "#" * 50)
            print(f"【INPUT 场景上文 → {U[t[0]]['uid']} 之前】")
            for u in ctx[-12:]:  # 只示末 12 句，够看
                print(f"  {u['uid']}│{u['text']}")
            print(f"【TARGET {char} 的回合】")
            for pos in t:
                u = U[pos]
                print(f"  〔{'/'.join(mine[pos])}〕{u['text']}")
            shown += 1


if __name__ == "__main__":
    main()
