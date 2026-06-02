#!/usr/bin/env python3
"""
render_chapter.py —— 把一章渲染成 Phase 2 标注用的【紧凑文本视图】。

为什么存在: subagent 做 Phase 2 时, 原先要(1)Read 整篇 pretty-print JSON(缩进+逐句
拆对象, 体积是纯正文的 ~5 倍)再(2)读 dialogue.py 带上下文窗口的输出(窗口互相重叠)。
两份输入承载的是同一段正文, 高度冗余。本脚本一次性给出无损且不重叠的两块:

  [全文]      每句一行 `scene_sent│text` —— 提供完整上下文(替代 Read 整篇 JSON)。
  [待标台词]  `uid \t 台词` —— 权威 uid 集合(替代 dialogue.py 的 ctx 窗口输出)。
              uid 逻辑直接复用 dialogue.py(同一套引号规则/qidx 后缀), 保证与
              phase2_eval.py 的覆盖校验对齐。

正文已整段 inline, "往回滚/查上下文"本就免费, 故不再附窗口。

用法:
  python3 render_chapter.py jsons/旅途余白.json
  python3 render_chapter.py maintext/卷01.json
"""
import sys, os, argparse
import dialogue  # 复用 load / extract / OUTER —— uid 与引号规则的唯一真源


def render(doc, source):
    lines = []
    lines.append(f"# === 全文（按 scene_sent 标号；台词行内含“ ”引号） ===")
    lines.append(f"# 篇名：{source}　scenes={len(doc.get('scenes', []))}")
    for sc in doc.get("scenes", []):
        chap = sc.get("chapter")
        head = f"## scene {sc['id']}" + (f"　〔原章：{chap}〕" if chap else "")
        lines.append(head)
        for s in sc["sents"]:
            t = s["text"].replace("\t", " ").replace("\n", " ")
            lines.append(f"{sc['id']}_{s['id']}│{t}")

    rows, _ = dialogue.extract(doc, source)
    lines.append("")
    lines.append(f"# === 待标台词 uid（共 {len(rows)} 条；标注集合 = 此列表，不多不少） ===")
    for r in rows:
        # r = [uid, source, scene, sent, qidx, content, context]
        lines.append(f"{r[0]}\t{r[5]}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="单个 json（jsons/ 或 maintext/）")
    args = ap.parse_args()
    doc = dialogue.load(args.path)
    src = doc.get("title") or os.path.splitext(os.path.basename(args.path))[0]
    sys.stdout.write(render(doc, src) + "\n")


if __name__ == "__main__":
    main()
