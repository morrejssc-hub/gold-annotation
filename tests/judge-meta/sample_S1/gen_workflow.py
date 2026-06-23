#!/usr/bin/env python3
"""把 judge_payload.json + q_schema.json 嵌进 judge.workflow.js（workflow 脚本无 fs 访问）。
workflow = Claude 判官臂逐条 fan-out：9 个 agent 各盲判一段，schema 强约束输出 Q1-Q10。"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
P = json.loads((HERE/"judge_payload.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((HERE/"q_schema.json").read_text(encoding="utf-8"))

js = f"""export const meta = {{
  name: 's1-claude-judge-fanout',
  description: 'S1样板·Claude判官臂逐条fan-out盲判(每段一个干净subagent，schema约束Q1-Q10)',
  phases: [{{ title: 'Judge', detail: '9段并行，各一judge subagent' }}],
}}

const SYSTEM = {json.dumps(P['system'], ensure_ascii=False)};
const HEAD = {json.dumps(P['head'], ensure_ascii=False)};
const ITEMS = {json.dumps(P['items'], ensure_ascii=False)};
const SCHEMA = {json.dumps(SCHEMA, ensure_ascii=False)};

const results = await parallel(ITEMS.map(it => () =>
  agent(
    SYSTEM + "\\n\\n" + HEAD +
    "\\n\\n## 待判回应（只对这一段按 Q1–Q10 打分）\\n[" + it.id + "]\\n" + it.text,
    {{ label: 'judge:' + it.id, phase: 'Judge', schema: SCHEMA }}
  ).then(r => ({{ id: it.id, scores: r }}))
));

return results.filter(Boolean);
"""
(HERE/"judge.workflow.js").write_text(js, encoding="utf-8")
print("wrote judge.workflow.js")
