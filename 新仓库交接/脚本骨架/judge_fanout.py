#!/usr/bin/env python3
"""通用判官逐条 fan-out 骨架。每段一次独立调用(去批内顺序/疲劳混淆)。
判官 system 须含：场景+关系头+正典原文短节选+严禁抠字眼+深度隔离(见 04_判官协议.md)。
JUDGE=glm 走 dashscope API；JUDGE=codex 走 codex-cli。→ scores.<judge>.json"""
import json, re, sys, time, subprocess, urllib.request
from pathlib import Path

JUDGE = sys.argv[1] if len(sys.argv) > 1 else "glm"
# payload: {"system":判官system, "head":场景+评分项Q1..Qn, "items":[{"id","text"}]}
P = json.loads(Path("judge_payload.json").read_text(encoding="utf-8"))
NQ = P.get("n_items", 10)                      # 评分项数量
SCHEMA = {"type": "object", "additionalProperties": False,
          "properties": {f"Q{i}": {"type": "integer", "minimum": 1, "maximum": 5} for i in range(1, NQ + 1)},
          "required": [f"Q{i}" for i in range(1, NQ + 1)]}

def unwrap(d):
    if "Q1" in d: return d
    for v in d.values():
        if isinstance(v, dict) and "Q1" in v: return v
    return d

def prompt(it):
    return P["head"] + f"\n\n## 待判回应（只对这一段按 Q1–Q{NQ} 打分，只输出 JSON）\n[{it['id']}]\n{it['text']}"

def call_glm(it):
    KEY = Path(".dashscope_key").read_text().strip()
    body = json.dumps({"model": "glm-5.2", "temperature": 0.2, "max_tokens": 6000,
        "messages": [{"role": "system", "content": P["system"]}, {"role": "user", "content": prompt(it)}]}).encode()
    req = urllib.request.Request("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        data=body, method="POST", headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        c = json.loads(r.read().decode())["choices"][0]["message"]["content"]
    return unwrap(json.loads(re.search(r"\{.*\}", re.sub(r"```(?:json)?", "", c), re.S).group(0)))

def call_codex(it):
    Path("q_schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
    guard = "（只依据下面文字打分。不要读取任何文件、不要用工具、不要探索仓库。只输出符合 schema 的 JSON。）\n\n"
    pr = guard + P["system"] + "\n\n" + prompt(it)
    outf = Path(f"_codex_{it['id']}.json")
    subprocess.run(["codex", "exec", "--skip-git-repo-check", "-s", "read-only",
        "--dangerously-bypass-approvals-and-sandbox", "--output-schema", "q_schema.json",
        "-o", str(outf), "-"], input=pr, text=True, capture_output=True, timeout=240)
    return unwrap(json.loads(re.search(r"\{.*\}", outf.read_text(), re.S).group(0)))

CALL = {"glm": call_glm, "codex": call_codex}[JUDGE]
scores = {}
for it in P["items"]:
    for a in range(4):
        try:
            s = CALL(it); scores[it["id"]] = {f"Q{i}": s[f"Q{i}"] for i in range(1, NQ + 1)}
            print(it["id"], "ok"); break
        except Exception as e:
            print(it["id"], f"retry{a}: {e}", file=sys.stderr)
            if a == 3: raise
            time.sleep(6)
Path(f"scores.{JUDGE}.json").write_text(json.dumps({"_judge": JUDGE, "scores": scores}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"done {len(scores)}")
