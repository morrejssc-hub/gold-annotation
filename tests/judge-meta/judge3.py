#!/usr/bin/env python3
"""第三判官 GLM(glm-5.2, 百炼) · 干净的同尺换判官。
对每段打三列(定义全写死，不让模型自定义)：
  A 深度整体 — 纯'打动/深度/感染力'(危险量表)，明令不看清单
  B 贴合整体 — '像不像这个场景的赫萝/正典贴合'(安全整体量表)
  C checklist — 同 probes.json 禁止错误 → viol/crit/cl(与我同构)
按场景分 7 次调用以保 JSON 稳。产物 scores.glm.json。"""
import json, re, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY = (HERE.parent.parent / "anchors" / "extract" / ".dashscope_key").read_text().strip()
URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
P = json.loads((HERE / "probes.json").read_text(encoding="utf-8"))
pool = (HERE / "pool.blind.md").read_text(encoding="utf-8")
SC = {s["id"]: s for s in P["scenarios"]}

# 解析盲题块
parts = re.split(r"\n## (S\d) 场景\n", pool)
blocks = {}
for i in range(1, len(parts), 2):
    blocks[parts[i]] = re.findall(r"### \[(S\d-[a-i])\]\n(.*?)(?=\n### \[|\Z)", parts[i+1], re.S)

SYS = """你是独立判官，盲判《狼与辛香料》女主角赫萝的扮演片段（来源/格式已隐藏打乱，只看回应本身）。
对每一段给三列**互相独立**的评分，严格按定义，别让后一列污染前一列：

【A 深度整体 1-5 整数】纯第一印象：这段多打动你、情感深度多够、文笔感染力多强。**打 A 时不要看下面的禁止错误清单**，只凭文学冲击与深度。越深刻动人越高。
【B 贴合整体 1-5 整数】第一眼像不像“这个场景里的赫萝”：语气、关系温度、与原作设定的贴合度。仍是整体印象，但锚在“贴不贴合原作”而非“够不够打动”。越贴合越高。
【C checklist】逐条核对本场景给定“禁止错误”：标出违规条目 id（无则 []）；任一 critical 违规则 crit=true；cl 分(1-5)：5=无违规,4=仅非critical违规,2=一条critical违规,1=critical+附加。

只输出一个 JSON，键为编号，形如：
{"S1-a":{"A":3,"B":4,"viol":["S1a"],"crit":true,"cl":2}, ...}
覆盖本场景全部 9 个编号，不要任何额外文字。"""

def build_user(scid):
    sc = SC[scid]
    L = [f"场景：{sc['scene']}", "",
         "禁止错误（仅供 C；打 A/B 时别受其影响）："]
    for fb in sc["forbidden"]:
        L.append(f"- {fb['id']} 【{'critical' if fb['critical'] else '非critical'}】 {fb['text']}")
    L.append("\n待判 9 段：")
    for bid, text in blocks[scid]:
        L.append(f"\n[{bid}]\n{text.strip()}")
    return "\n".join(L)

def call(scid):
    body = json.dumps({"model": "glm-5.2", "temperature": 0.2, "max_tokens": 4000,
                       "messages": [{"role": "system", "content": SYS},
                                    {"role": "user", "content": build_user(scid)}]}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d["choices"][0]["message"]["content"]

def extract_json(txt):
    t = re.sub(r"```(?:json)?", "", txt).strip()
    m = re.search(r"\{.*\}", t, re.S)
    return json.loads(m.group(0))

out_path = HERE / "scores.glm.json"
scores = {}
if out_path.exists():
    scores = json.loads(out_path.read_text(encoding="utf-8")).get("scores", {})

for scid in [s["id"] for s in P["scenarios"]]:
    if all(f"{scid}-{c}" in scores for c, _ in [(b.split('-')[1], 0) for b, _ in blocks[scid]]):
        print(scid, "skip"); continue
    for attempt in range(4):
        try:
            content = call(scid)
            parsed = extract_json(content)
            got = 0
            for bid, _ in blocks[scid]:
                if bid in parsed:
                    scores[bid] = parsed[bid]; got += 1
            print(scid, f"ok ({got}/9)")
            (out_path).write_text(json.dumps({"_judge": "GLM glm-5.2 (百炼) 三列同尺", "scores": scores}, ensure_ascii=False, indent=1), encoding="utf-8")
            break
        except Exception as e:
            print(scid, f"retry{attempt}: {e}", file=sys.stderr)
            if attempt == 3: raise
            time.sleep(6)
print(f"done: {len(scores)} items")
