#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""roll-forward 切点器（零 AI）。

从 maintext/卷NN.json 或 jsons/<篇>.json 切一个 roll-forward 题面：
  - [左侧上文]：场景内 切点(含) 之前的句子，喂两臂生成器；
  - [挖空·判后揭]：切点之后 N 句原文，作为 held-out（判完再揭，别先给）。

文档结构沿用全项目：doc.scenes[].sents[]，每句 {id, text}，句号=sceneid_sentid。

用法：
  python3 rollforward.py maintext/卷02.json --scene 7 --cut 24
  python3 rollforward.py jsons/旅途余白.json --scene 2 --cut 48 --window 14 --heldout 8
"""
import argparse
import json
import sys


def load_scene(path, scene_id):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    doc = d.get("doc", d)
    scenes = doc.get("scenes", [])
    for s in scenes:
        if str(s.get("id")) == str(scene_id):
            return doc, s
    ids = ", ".join(str(s.get("id")) for s in scenes)
    sys.exit(f"[err] scene {scene_id} 不在 {path}；可选 scene id: {ids}")


def main():
    ap = argparse.ArgumentParser(description="roll-forward 切点器")
    ap.add_argument("source", help="maintext/卷NN.json 或 jsons/<篇>.json")
    ap.add_argument("--scene", required=True, help="scene id")
    ap.add_argument("--cut", required=True, type=int,
                    help="切点 sent id（含此句进上文，之后挖空）")
    ap.add_argument("--window", type=int, default=0,
                    help="只取切点前 K 句作上文（0=场景开头到切点全给）")
    ap.add_argument("--heldout", type=int, default=8, help="揭 N 句 held-out")
    a = ap.parse_args()

    doc, scene = load_scene(a.source, a.scene)
    sents = scene.get("sents", [])
    idx = next((i for i, s in enumerate(sents) if s.get("id") == a.cut), None)
    if idx is None:
        ids = ", ".join(str(s.get("id")) for s in sents)
        sys.exit(f"[err] cut sent {a.cut} 不在 scene {a.scene}；可选 sent id: {ids}")

    lo = 0 if a.window <= 0 else max(0, idx - a.window + 1)
    left = sents[lo:idx + 1]
    held = sents[idx + 1: idx + 1 + a.heldout]

    src = a.source.split("/")[-1].rsplit(".", 1)[0]
    foc = doc.get("focalizer", "")
    print(f"# roll-forward · {src} · scene {a.scene} · cut {a.scene}_{a.cut}"
          + (f" · focalizer={foc}" if foc else ""))
    print(f"\n## [左侧上文]（逐字喂两臂；{a.scene}_{left[0]['id']} … {a.scene}_{a.cut}）")
    for s in left:
        print(f"{a.scene}_{s['id']}\t{s.get('text','')}")
    print(f"\n## [挖空·判后揭] held-out（{len(held)} 句，判完再对照）")
    for s in held:
        print(f"{a.scene}_{s['id']}\t{s.get('text','')}")
    if not held:
        print("(切点在场景末尾，无 held-out)")


if __name__ == "__main__":
    main()
