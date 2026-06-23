#!/usr/bin/env python3
"""GLM 判官臂逐条 fan-out：每段一次独立调用(去批内顺序/疲劳混淆)。→ scores.glm.json"""
import json, re, sys, time, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent
KEY = (HERE.parent.parent.parent/"anchors"/"extract"/".dashscope_key").read_text().strip()
URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
PAYLOAD = sys.argv[1] if len(sys.argv)>1 else "judge_payload.json"
OUT = sys.argv[2] if len(sys.argv)>2 else "scores.glm.json"
P = json.loads((HERE/PAYLOAD).read_text(encoding="utf-8"))

def call(item):
    user = P["head"] + f"\n\n## 待判回应（只对这一段按 Q1–Q10 打分，只输出 JSON {{\"Q1\":x,...,\"Q10\":x}}）\n[{item['id']}]\n{item['text']}"
    body = json.dumps({"model":"glm-5.2","temperature":0.2,"max_tokens":6000,
        "messages":[{"role":"system","content":P["system"]},{"role":"user","content":user}]}).encode()
    req = urllib.request.Request(URL,data=body,method="POST",
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
    with urllib.request.urlopen(req,timeout=180) as r:
        c = json.loads(r.read().decode())["choices"][0]["message"]["content"]
    t = re.sub(r"```(?:json)?","",c).strip()
    d = json.loads(re.search(r"\{.*\}",t,re.S).group(0))
    if "Q1" not in d:  # GLM 可能多包一层 {"A1":{...}}
        for v in d.values():
            if isinstance(v, dict) and "Q1" in v:
                d = v; break
    return d

scores={}
for it in P["items"]:
    for a in range(4):
        try:
            s=call(it); scores[it["id"]]={k:s[k] for k in [f"Q{i}" for i in range(1,11)]}
            print(it["id"],"ok",scores[it["id"]]); break
        except Exception as e:
            print(it["id"],f"retry{a}: {e}",file=sys.stderr)
            if a==3: raise
            time.sleep(6)
(HERE/OUT).write_text(json.dumps({"_judge":f"GLM glm-5.2 逐条fanout ({PAYLOAD})","scores":scores},ensure_ascii=False,indent=1),encoding="utf-8")
print(f"done {len(scores)}")
