#!/usr/bin/env python3
"""通用 actor 生成骨架（参数化，provider 可切）。
被测模型对一组场景多次采样，原始落 raw.jsonl。无三方依赖（urllib）。
用法：填 PROVIDER / KEY_FILE / SCENES，python3 gen_actor.py"""
import json, sys, time, urllib.request
from pathlib import Path

# ---- 配置（换 provider 只改这里）----
PROVIDERS = {
    "deepseek": {"url": "https://api.deepseek.com/chat/completions", "model": "deepseek-v4-pro"},
    "dashscope": {"url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "model": "glm-5.2"},
}
PROVIDER = "deepseek"
KEY = Path(".actor_key").read_text().strip()   # gitignored key 文件
TEMP, MAXTOK, N = 0.8, 2500, 3                  # 采样温度 / max_tokens(reasoning模型给足) / 每场景采样数

# SCENES: [{"id","system"(角色扮演指令), "user"(场景文本=关系头+情景)}]
SCENES = json.loads(Path("scenes.json").read_text(encoding="utf-8"))

cfg = PROVIDERS[PROVIDER]
out = Path("raw.jsonl")
done = {json.loads(l)["custom_id"] for l in out.read_text().splitlines()} if out.exists() else set()

def call(system, user):
    body = json.dumps({"model": cfg["model"], "temperature": TEMP, "max_tokens": MAXTOK,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(cfg["url"], data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())["choices"][0]["message"]

with out.open("a", encoding="utf-8") as f:
    for sc in SCENES:
        for i in range(1, N + 1):
            cid = f"{sc['id']}__{i}"
            if cid in done: continue
            for a in range(4):
                try:
                    m = call(sc["system"], sc["user"])
                    f.write(json.dumps({"custom_id": cid, "scene": sc["id"], "sample": i,
                        "content": m.get("content", ""), "reasoning": m.get("reasoning_content", "")},
                        ensure_ascii=False) + "\n"); f.flush()
                    print(cid, "ok"); break
                except Exception as e:
                    print(cid, f"retry{a}: {e}", file=sys.stderr)
                    if a == 3: raise
                    time.sleep(6)
print("done")
