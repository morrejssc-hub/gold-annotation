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
import sys, os, json, argparse
import dialogue  # 复用 load / extract / OUTER —— uid 与引号规则的唯一真源

HERE = os.path.dirname(os.path.abspath(__file__))


def load_cast(source):
    """读 casts/<篇>.json；没有就返回 None（[在场] 退化为不输出）。"""
    p = os.path.join(HERE, "casts", source + ".json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def scene_present(cast, scene_text):
    """机械 alias 匹配：本 scene 文本里点名出现、且 present:true 的角色 canonical 集。
    只认 canonical/aka 这些"名/专名"串：appellations（老板/先生/祭司…）是视角相对称谓，
    会误报（如议论中的'祭司'把仪式祭司算进非其在场的 scene），按约束#2 不用来驱动在场判定；
    纯职称实体（议长/领路的祭司）靠 canonical 本身即职称来命中，群体（…老板们）可能漏——无妨，
    群体多为 playable:false。descriptors 多为'他/先生'类泛指，亦排除。
    focalizer 按定义全程在场，恒列入。recall 取向：仅靠代词/未称呼出场者可能漏，作辅助提示用，模型仍读全文。"""
    if not cast:
        return None
    present, foc = [], None
    for c in cast.get("cast", []):
        if c.get("is_focalizer"):
            foc = c["canonical"]
        if not c.get("present"):
            continue
        keys = [c["canonical"], *c.get("aka", [])]
        if any(k and k in scene_text for k in keys):
            present.append(c["canonical"])
    if foc and foc not in present:
        present.insert(0, foc)
    # 维持 cast 声明顺序，focalizer 置首
    order = {c["canonical"]: i for i, c in enumerate(cast.get("cast", []))}
    rest = sorted([x for x in present if x != foc], key=lambda x: order.get(x, 99))
    return ([foc] if foc else []) + rest


def render(doc, source, cast=None):
    lines = []
    lines.append(f"# === 全文（按 scene_sent 标号；台词行内含“ ”引号） ===")
    lines.append(f"# 篇名：{source}　scenes={len(doc.get('scenes', []))}")
    if cast:
        lines.append(f"# scene 头 [在场] = 本节点名出现的角色（机械匹配，辅助闭集；以正文为准）")
    for sc in doc.get("scenes", []):
        chap = sc.get("chapter")
        sc_text = "".join(s["text"] for s in sc["sents"])
        present = scene_present(cast, sc_text)
        tag = f"　[在场：{', '.join(present)}]" if present else ""
        head = f"## scene {sc['id']}" + (f"　〔原章：{chap}〕" if chap else "") + tag
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
    sys.stdout.write(render(doc, src, load_cast(src)) + "\n")


if __name__ == "__main__":
    main()
