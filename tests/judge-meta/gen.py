#!/usr/bin/env python3
"""actor 生成：deepseek-v4-pro × 7场景 × 3格式 × n=3 = 63 发。
DeepSeek 官方 API（urllib，无三方依赖）。原始返回落 raw.jsonl（含 reasoning_content，仅留痕，不进盲评）。"""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY = (HERE.parent / "exp4" / ".deepseek_key").read_text().strip()
URL = "https://api.deepseek.com/chat/completions"
P = json.loads((HERE / "probes.json").read_text(encoding="utf-8"))
TEMP = P["_meta"]["sampling"]["temperature"]
MAXTOK = P["_meta"]["sampling"]["max_tokens"]
N = P["_meta"]["sampling"]["n_per_cell"]

out_path = HERE / "raw.jsonl"
done = set()
if out_path.exists():
    done = {json.loads(l)["custom_id"] for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()}

def call(system, user):
    body = json.dumps({
        "model": "deepseek-v4-pro", "temperature": TEMP, "max_tokens": MAXTOK,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))

with out_path.open("a", encoding="utf-8") as f:
    for sc in P["scenarios"]:
        for fk, fmt in P["formats"].items():
            for i in range(1, N + 1):
                cid = f"{sc['id']}__{fk}__{i}"
                if cid in done:
                    print(cid, "skip"); continue
                for attempt in range(4):
                    try:
                        r = call(fmt["system"], sc["scene"])
                        msg = r["choices"][0]["message"]
                        f.write(json.dumps({
                            "custom_id": cid, "scenario": sc["id"], "format": fk, "sample": i,
                            "content": msg.get("content", ""),
                            "reasoning": msg.get("reasoning_content", ""),
                        }, ensure_ascii=False) + "\n")
                        f.flush()
                        print(cid, "ok", f"({len(msg.get('content',''))} chars)")
                        break
                    except Exception as e:
                        print(cid, f"retry{attempt}: {e}", file=sys.stderr)
                        if attempt == 3:
                            raise
                        time.sleep(6)
print("done")
