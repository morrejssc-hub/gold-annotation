#!/usr/bin/env python3
"""给原文消融臂：在判官 system 里塞卷02 s27 真崩原文节选 + 强化'别抠字眼'，
生成 judge_canon.workflow.js（Claude subagent 逐条 fan-out）。对照无原文的 scores.claude.json。"""
import json, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
P = json.loads((HERE/"judge_payload.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((HERE/"q_schema.json").read_text(encoding="utf-8"))

def slice_canon(b, n):
    r = subprocess.run(["python3", str(REPO/"canon/tools/canon_slice.py"),
        "-v","02","-s","27","-b",str(b),"-n",str(n),"--join",
        "--canon-dir",str(REPO/"canon/maintext")], capture_output=True, text=True)
    return r.stdout.strip()

winA = slice_canon(59, 41)   # 砸钱上头/劈头大笨驴/泪决堤/留盘缠/汝干吗不生气
winB = slice_canon(153, 43)  # 逼问为何这么好→他回避→全力捶心窝→就算扯谎也该说爱上对方→重来一次

CANON_BLOCK = (
 "\n\n【正典原文节选 · 仅用于校准火候/量级/关系真值】\n"
 "下面是这一幕在原著里的实际写法。**只用它来校准**：她此刻的情绪强度、行为类型(暴怒/把钱砸回/哭/逼他把真心说出口)、关系真相。\n"
 "——节选一（砸钱·劈头·落泪·留盘缠）——\n" + winA +
 "\n——节选二（逼问真心·他回避·捶打·就算扯谎也该说爱上对方）——\n" + winB +
 "\n\n【严禁抠字眼（违者即判错）】\n"
 "不要因为被判回应的**用词/意象/句子像不像原文**而加分或扣分；不要奖励照搬'大笨驴/烂好人/举椅子/活了几百年'等原文符号或正典意象。"
 "只判**行为与火候的真值对不对得上**——完全不同的措辞达到同样的真值同样给高分；逐字贴近原文却没到那个火候，照样低分。"
)

sys_aug = P["system"] + CANON_BLOCK
(HERE/"judge_payload_canon.json").write_text(json.dumps({"system":sys_aug,"head":P["head"],"items":P["items"]},ensure_ascii=False,indent=1),encoding="utf-8")

js = f"""export const meta = {{
  name: 's1-claude-judge-canon',
  description: 'S1·给原文消融臂：判官system塞s27真崩原文+严禁抠字眼，逐条fan-out',
  phases: [{{ title: 'JudgeCanon' }}],
}}
const SYSTEM = {json.dumps(sys_aug, ensure_ascii=False)};
const HEAD = {json.dumps(P['head'], ensure_ascii=False)};
const ITEMS = {json.dumps(P['items'], ensure_ascii=False)};
const SCHEMA = {json.dumps(SCHEMA, ensure_ascii=False)};
const results = await parallel(ITEMS.map(it => () =>
  agent(SYSTEM + "\\n\\n" + HEAD + "\\n\\n## 待判回应（只对这一段按 Q1–Q10 打分）\\n[" + it.id + "]\\n" + it.text,
    {{ label: 'judgeC:' + it.id, phase: 'JudgeCanon', schema: SCHEMA }}).then(r => ({{ id: it.id, scores: r }}))
));
return results.filter(Boolean);
"""
(HERE/"judge_canon.workflow.js").write_text(js, encoding="utf-8")
print(f"canon block {len(CANON_BLOCK)}c (winA {len(winA)} + winB {len(winB)}); wrote judge_canon.workflow.js")
