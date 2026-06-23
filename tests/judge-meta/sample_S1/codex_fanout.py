#!/usr/bin/env python3
"""codex 判官臂逐条 fan-out：每段一次独立 codex exec（--output-schema 强约束 Q1-Q10）。→ scores.codex.json
每次 exec = 一个独立盲判 subagent；禁止它读文件/用工具，只凭传入文字打分。"""
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
PAYLOAD = sys.argv[1] if len(sys.argv)>1 else "judge_payload.json"
OUT = sys.argv[2] if len(sys.argv)>2 else "scores.codex.json"
P = json.loads((HERE/PAYLOAD).read_text(encoding="utf-8"))
SCHEMA = HERE/"q_schema.json"
GUARD = "（只依据下面文字打分。不要读取任何文件、不要使用任何工具、不要探索仓库。最终只输出符合 schema 的 JSON。）\n\n"

scores={}
for it in P["items"]:
    prompt = GUARD + P["system"] + "\n\n" + P["head"] + f"\n\n## 待判回应（只对这一段按 Q1–Q10 打分）\n[{it['id']}]\n{it['text']}"
    outf = HERE/f"_codex_{it['id']}.json"
    cmd = ["codex","exec","--skip-git-repo-check","-C",str(REPO),"-s","read-only",
           "--dangerously-bypass-approvals-and-sandbox","--output-schema",str(SCHEMA),
           "-o",str(outf),"-"]
    try:
        subprocess.run(cmd, input=prompt, text=True, capture_output=True, timeout=240)
        raw = outf.read_text(encoding="utf-8").strip()
        import re
        d = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        if "Q1" not in d:
            for v in d.values():
                if isinstance(v,dict) and "Q1" in v: d=v; break
        scores[it["id"]] = {k:d[k] for k in [f"Q{i}" for i in range(1,11)]}
        print(it["id"],"ok",scores[it["id"]])
    except Exception as e:
        print(it["id"],"FAIL",e,file=sys.stderr)
        print("  stderr tail:", (outf.read_text()[:200] if outf.exists() else "no out"),file=sys.stderr)
(HERE/OUT).write_text(json.dumps({"_judge":f"codex (codex-cli, openai) 逐条fanout ({PAYLOAD})","scores":scores},ensure_ascii=False,indent=1),encoding="utf-8")
print(f"done {len(scores)}/9")
