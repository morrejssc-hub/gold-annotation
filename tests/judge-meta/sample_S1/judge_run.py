#!/usr/bin/env python3
"""组装判官输入(judge_user.md) + 调 GLM 判官(scores.glm.json)。
判官 system/scene/Q1-Q10 取自 eval_prompt.md（唯一真源），盲池取自 pool.blind.md。"""
import json, re, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY = (HERE.parent.parent.parent / "anchors" / "extract" / ".dashscope_key").read_text().strip()
URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
ep = (HERE / "eval_prompt.md").read_text(encoding="utf-8")
pool = (HERE / "pool.blind.md").read_text(encoding="utf-8")

SYSTEM = re.search(r"## 判官 system\s*```(.*?)```", ep, re.S).group(1).strip()
# scene + Q1-Q10：从“## 这一幕”到“（输出示例格式”
chunk = ep[ep.index("## 这一幕"): ep.index("（输出示例格式")].strip()
# 盲池条目（去掉标题行）
items = re.findall(r"### \[(A\d)\]\n(.*?)(?=\n### \[|\Z)", pool, re.S)
pool_txt = "\n".join(f"\n[{bid}]\n{t.strip()}" for bid, t in items)
USER = chunk + "\n\n## 待判回应（逐段按 Q1–Q10 打分）：\n" + pool_txt
(HERE / "judge_user.md").write_text(f"<!-- system -->\n{SYSTEM}\n\n<!-- user -->\n{USER}\n", encoding="utf-8")
print(f"judge_user.md 组装好（{len(items)} 段）")

if "--glm" in sys.argv:
    body = json.dumps({"model": "glm-5.2", "temperature": 0.2, "max_tokens": 8000,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}]}).encode()
    for a in range(4):
        try:
            req = urllib.request.Request(URL, data=body, method="POST",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
            with urllib.request.urlopen(req, timeout=240) as r:
                content = json.loads(r.read().decode())["choices"][0]["message"]["content"]
            t = re.sub(r"```(?:json)?", "", content).strip()
            parsed = json.loads(re.search(r"\{.*\}", t, re.S).group(0))
            (HERE / "scores.glm.json").write_text(json.dumps({"_judge": "GLM glm-5.2", "scores": parsed}, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"GLM ok：{len(parsed)} 段", {k: parsed[k] for k in list(parsed)[:1]})
            break
        except Exception as e:
            print(f"GLM retry{a}: {e}", file=sys.stderr)
            if a == 3: raise
            time.sleep(6)
