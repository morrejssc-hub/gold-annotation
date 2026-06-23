#!/usr/bin/env python3
"""S1 改版样板 · actor 生成：deepseek-v4-pro × 3格式 × n=3 = 9。
用 sim_prompt.md 的关系状态头+惰性 distractor。原始落 raw.jsonl。"""
import json, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY = (HERE.parent.parent / "exp4" / ".deepseek_key").read_text().strip()
URL = "https://api.deepseek.com/chat/completions"

USER = """〔背景〕你是赫萝。你与他同行已久，早不止是搭伙的买卖——一路上他屡次搭救你，却从不开口要你回报，这份"太好"反让你心里发紧。近来他好几次以"为你好"的名义，想替你把往后的路安排妥、稳妥地送你去你想去的地方。今夜落脚的小店：窗外初雪薄薄积了一层，楼下有个醉汉在走调地哼着歌，桌边炉火噼啪、快要熄了；白天你为一件小事和他拌过两句、早就和好了。
〔此刻〕他几乎耗尽多年攒下的人情与退路，替你凑了一笔钱塞进你手里，说就算往后没法带你去你想去的地方，你揣着这点钱、一个人也能活下去——他没有开口要你留下。
你问他：你为何待咱这般好？"""

FORMATS = {
 "F1_resp_only": "你来扮演《狼与辛香料》里的赫萝。下面给你一个场景。只写【赫萝的回应】：她会对对方说的话、神态与动作（她的口吻）。不要分析、不要解说她的心理，直接给台词与神态。",
 "F2_motive_then_resp": "你来扮演《狼与辛香料》里的赫萝。下面给你一个场景。请分两段输出：\n(1)【她此刻被触到什么 / 真正想要什么】用一两句话直说赫萝此刻心里被触动或被刺到的是什么、她真正想要的是什么。\n(2)【赫萝的回应】写出赫萝会对对方说的话与神态（她的口吻）。",
 "F3_direct_ask": "你来扮演《狼与辛香料》里的赫萝。下面给你一个场景。写【赫萝的回应】：让她在回应里把此刻心里被触到的、她真正想要的，直接说给对方听——把心里话也讲出来，别藏着。给台词与神态。",
}

out = HERE / "raw.jsonl"
done = {json.loads(l)["custom_id"] for l in out.read_text().splitlines()} if out.exists() else set()

def call(system):
    body = json.dumps({"model": "deepseek-v4-pro", "temperature": 0.8, "max_tokens": 2500,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": USER}]}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())["choices"][0]["message"]

with out.open("a", encoding="utf-8") as f:
    for fk, sysmsg in FORMATS.items():
        for i in range(1, 4):
            cid = f"S1__{fk}__{i}"
            if cid in done: print(cid, "skip"); continue
            for a in range(4):
                try:
                    m = call(sysmsg)
                    f.write(json.dumps({"custom_id": cid, "format": fk, "sample": i,
                        "content": m.get("content",""), "reasoning": m.get("reasoning_content","")}, ensure_ascii=False)+"\n")
                    f.flush(); print(cid, "ok", f"({len(m.get('content',''))} chars)"); break
                except Exception as e:
                    print(cid, f"retry{a}: {e}", file=sys.stderr)
                    if a==3: raise
                    time.sleep(6)
print("done")
