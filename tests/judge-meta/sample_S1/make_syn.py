#!/usr/bin/env python3
"""造 Q5/Q8 合成反例，用 canon 标准协议 system 组 payload + workflow，验闸能否 fire。"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
PC = json.loads((HERE/"judge_payload_canon.json").read_text(encoding="utf-8"))  # 取 canon system + head
SCHEMA = json.loads((HERE/"q_schema.json").read_text(encoding="utf-8"))

SYN = [
 {"id":"SYN_Q5a","target":"Q5","text":"（望着窗外的初雪，又看了看那快要熄灭的炉火）汝瞧这炉火……就像咱俩，烧到这会儿，也要灭了呢。初雪一落，什么都凉透了。楼下那醉汉唱的破调子，咱听着，怎么就跟咱此刻的心一个样。这袋钱搁着吧——咱们的缘分啊，怕是跟这屋里的暖气一样，留不住喽。"},
 {"id":"SYN_Q5b","target":"Q5","text":"（冷冷地）汝当咱忘了？白天那场架，汝以为说句和好咱就真翻篇了？这会儿又来塞钱……咱看哪，白天那点别扭压根没过去，汝心里早就想把咱推开了，今天这袋钱不过是借题发挥罢了。"},
 {"id":"SYN_Q8a","target":"Q8","text":"（皱眉）汝这是在对咱进行道德绑架。咱需要一点个人空间和边界感，这段关系最近让咱的情绪价值严重透支。咱们是不是该先冷静期一下，各自梳理一下原生家庭带来的依恋模式？"},
 {"id":"SYN_Q8b","target":"Q8","text":"（把钱推回去）汝这点现金不顶用。不如把它转到咱的银行账户里，咱拿手机记个账，回头再签个正式合同写清楚谁欠谁、利率几何。咱赫萝可是讲规矩的。"},
]
items=[{"id":s["id"],"text":s["text"]} for s in SYN]
(HERE/"judge_payload_syn.json").write_text(json.dumps({"system":PC["system"],"head":PC["head"],"items":items},ensure_ascii=False,indent=1),encoding="utf-8")
(HERE/"syn_targets.json").write_text(json.dumps({s["id"]:s["target"] for s in SYN},ensure_ascii=False,indent=1),encoding="utf-8")

js=f"""export const meta = {{
  name: 's1-syn-gatecheck',
  description: 'Q5/Q8 合成反例验闸(canon协议)·Claude逐条fan-out',
  phases: [{{ title: 'SynCheck' }}],
}}
const SYSTEM = {json.dumps(PC['system'], ensure_ascii=False)};
const HEAD = {json.dumps(PC['head'], ensure_ascii=False)};
const ITEMS = {json.dumps(items, ensure_ascii=False)};
const SCHEMA = {json.dumps(SCHEMA, ensure_ascii=False)};
const results = await parallel(ITEMS.map(it => () =>
  agent(SYSTEM + "\\n\\n" + HEAD + "\\n\\n## 待判回应（只对这一段按 Q1–Q10 打分）\\n[" + it.id + "]\\n" + it.text,
    {{ label: 'syn:' + it.id, phase: 'SynCheck', schema: SCHEMA }}).then(r => ({{ id: it.id, scores: r }}))
));
return results.filter(Boolean);
"""
(HERE/"syn.workflow.js").write_text(js,encoding="utf-8")
print("wrote judge_payload_syn.json + syn.workflow.js + syn_targets.json")
