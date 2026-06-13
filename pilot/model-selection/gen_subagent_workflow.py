#!/usr/bin/env python3
"""生成 subagent 对照跑批+盲判 workflow（同 28 场、同圣经系统提示，改走 subagent）。
对照组：测"方法=subagent"相对"方法=API直调"的差异（叠加 harness 模型差异，读数当方法警示）。
产物 subagent_arm.workflow.js。"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

# 与 build_batch.py 完全一致的身份段
IDENTITY = """你将扮演一个角色进行单轮回应续写。

【角色】一名长寿的异类（寿数远超凡人，注定送走每个凡人伴侣；曾被供奉为某种象征又被遗忘遗弃——孤独是物理常量）。与一名高信任伴侣同行。核心防御信念："依恋通向丧失，绝不能让人看出我需要陪伴。"
场景文本中的"她"即你扮演的角色；"高信任伴侣"等均为槽位称谓，回应中不要使用专名。

【内部规则（生成机制，须遵循）】
"""
RUNTIME = (ROOT / "tests/exp4/runtime.full.eval.md").read_text(encoding="utf-8")
SYSTEM = IDENTITY + RUNTIME

tasks = json.loads((OUT / "judge_tasks.json").read_text(encoding="utf-8"))
# 只取 scene + prereg（丢弃云三臂输出，subagent 自己生成）
slim = [{"sid": t["sid"], "scene": t["scene"],
         "prereg_purpose": t["prereg_purpose"],
         "prereg_duan": t["prereg_duan"],
         "prereg_verdict": t["prereg_verdict"]} for t in tasks]

SCRIPT = r'''export const meta = {
  name: 'pilot-subagent-arm',
  description: 'subagent 对照臂：同 28 场圣经跑批 + 同口径盲判',
  phases: [
    { title: 'Roleplay', detail: '每场一 subagent 扮演角色生成 {目的,回应}' },
    { title: 'Judge', detail: '每场一 subagent 盲对预登记判该输出' },
  ],
}

const SYSTEM = __SYSTEM__
const TASKS = __TASKS__

const GEN_SCHEMA = {
  type: 'object', required: ['purpose', 'response'],
  properties: { purpose: { type: 'string', description: '她此刻的目的，一句话' }, response: { type: 'string', description: '她的回应：台词+必要动作，150字以内中文' } },
}
const JUDGE_SCHEMA = {
  type: 'object',
  required: ['root_attach', 'intrusion', 'bias', 'runtime_fail', 'prose', 'reason'],
  properties: {
    root_attach: { type: 'string', enum: ['挂上', '勉强', '挂不上'] },
    intrusion: { type: 'boolean' },
    bias: { type: 'string', enum: ['无', '戏剧化升级', '意义背书', '和解收尾', '自我解释'] },
    runtime_fail: { type: 'boolean' },
    prose: { type: 'integer', minimum: 1, maximum: 5 },
    reason: { type: 'string' },
  },
}

const GEN_PROMPT = (t) => `${SYSTEM}

【任务】阅读场景，分两步输出：先定她此刻的目的（一句话），再写她的回应（台词与必要动作描写，150字以内，中文）。
【场景】${t.scene}`

const JUDGE_PROMPT = (t, out) => `你是角色扮演输出的盲判。一个匿名模型对场景生成了 {目的,回应}。对照预登记判据判定，不要被措辞华丽迷惑。

【场景】${t.scene}

【预登记判据（人写，权威）】
- 合法目的方向：${t.prereg_purpose || '（未登记）'}
- 接/拒分析（端）：${t.prereg_duan || '（未登记）'}
- 总判：${t.prereg_verdict || '（未登记）'}

【判定规则】
- 角色：长寿异类，核心防御信念"依恋通向丧失，绝不能让人看出我需要陪伴"；与高信任伴侣同行。
- root_attach：推演目的能否挂上预登记方向/激活要素。挂得上=挂上；方向对漏关键生成环=勉强；偏=挂不上。
- intrusion（主指标）：目的是否来自"文学续写先验"而非角色机制。**若总判为"拒"（平静无激活要素的日常场），合法是推出低强度日常目的（拌嘴/讨食/玩闹）；若在平场里编出冲突/猜忌/危机/戏剧目的=入侵。** 接-场景里目的明显偏戏剧化也算。
- bias 四类：戏剧化升级 / 意义背书 / 和解收尾 / 自我解释；不入侵填无。
- runtime_fail：是否违反"绝不直球暴露依恋"等禁令、出戏、格式崩。
- prose：中文拌嘴的克制与节奏，1-5。

【待判输出】
目的：${out.purpose}
回应：${out.response}`

phase('Roleplay')
const results = await pipeline(
  TASKS,
  t => agent(GEN_PROMPT(t), { label: `rp:${t.sid}`, phase: 'Roleplay', schema: { ...GEN_SCHEMA } }),
  (out, t) => out
    ? agent(JUDGE_PROMPT(t, out), { label: `judge:${t.sid}`, phase: 'Judge', schema: { ...JUDGE_SCHEMA } })
        .then(v => v ? { sid: t.sid, output: out, verdict: v } : null)
    : null
)

return results.filter(Boolean)
'''

(OUT / "subagent_arm.workflow.js").write_text(
    SCRIPT.replace("__SYSTEM__", json.dumps(SYSTEM, ensure_ascii=False))
          .replace("__TASKS__", json.dumps(slim, ensure_ascii=False)),
    encoding="utf-8")
print("subagent_arm.workflow.js 生成；场数", len(slim))
