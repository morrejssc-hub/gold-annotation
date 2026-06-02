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
import json, argparse


def scene_of(uid):
    return uid.split("_")[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("units"); ap.add_argument("--char", required=True)
    ap.add_argument("--scene", default=None, help="只看某 scene")
    ap.add_argument("--samples", type=int, default=0, help="渲染 N 个 (上文→回合) 样本")
    args = ap.parse_args()

    U = json.load(open(args.units, encoding="utf-8"))["units"]
    char = args.char
    # 该角色 involved 的句子位置 + role
    mine = {}  # pos -> roles set
    for i, u in enumerate(U):
        roles = sorted({x["role"] for x in u["involves"] if x["char"] == char})
        if roles:
            mine[i] = roles

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
    print(f"# {char} @ {args.units}")
    print(f"# 出现句 {len(mine)}（含说 {n_say} / 做 {sum(1 for p in mine if '做' in mine[p])}）；回合 {len(turns)}"
          + (f"（scene {args.scene}）" if args.scene else ""))
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
