#!/usr/bin/env python3
"""抽三臂共用判官 payload：{system, head(场景+Q1-Q10), items:[{id,text}]} → judge_payload.json
+ Q10 输出 schema → q_schema.json（codex --output-schema / workflow agent schema 用）。"""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
ep = (HERE/"eval_prompt.md").read_text(encoding="utf-8")
pool = (HERE/"pool.blind.md").read_text(encoding="utf-8")

system = re.search(r"## 判官 system\s*```(.*?)```", ep, re.S).group(1).strip()
head = ep[ep.index("## 这一幕"): ep.index("（输出示例格式")].strip()
items = [{"id": b, "text": t.strip()} for b, t in re.findall(r"### \[(A\d)\]\n(.*?)(?=\n### \[|\Z)", pool, re.S)]
(HERE/"judge_payload.json").write_text(json.dumps({"system": system, "head": head, "items": items}, ensure_ascii=False, indent=1), encoding="utf-8")

props = {f"Q{i}": {"type": "integer", "minimum": 1, "maximum": 5} for i in range(1, 11)}
schema = {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
(HERE/"q_schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"payload: {len(items)} items; system {len(system)}c; head {len(head)}c")
