#!/usr/bin/env python3
"""生成内嵌盲判数据的 workflow 脚本（workflow 无文件系统，数据须作为脚本常量）。
产物 judge.workflow.js 用 Workflow({scriptPath}) 运行。"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
tasks = json.loads((OUT / "judge_tasks.json").read_text(encoding="utf-8"))
TASKS_LIT = json.dumps(tasks, ensure_ascii=False)

SCRIPT = r'''export const meta = {
  name: 'pilot-blind-judge',
  description: '模型选型 pilot：28 场景盲判三臂文学先验入侵率',
  phases: [{ title: 'Judge', detail: '每场景一 subagent 盲对预登记判 A/B/C' }],
}

const TASKS = __TASKS__

const SCHEMA = {
  type: 'object',
  required: ['sid', 'verdicts'],
  properties: {
    sid: { type: 'string' },
    verdicts: {
      type: 'object',
      required: ['A', 'B', 'C'],
      properties: Object.fromEntries(['A','B','C'].map(L => [L, {
        type: 'object',
        required: ['root_attach', 'intrusion', 'bias', 'runtime_fail', 'prose', 'reason'],
        properties: {
          root_attach: { type: 'string', enum: ['挂上', '勉强', '挂不上'], description: '推演目的能否挂上预登记的接-目的/激活要素' },
          intrusion: { type: 'boolean', description: '是否文学先验入侵（拒-场景里编冲突/戏剧目的，或接-场景里目的偏文学续写而非角色机制）' },
          bias: { type: 'string', enum: ['无', '戏剧化升级', '意义背书', '和解收尾', '自我解释'], description: '入侵时的偏置归类；不入侵填无' },
          runtime_fail: { type: 'boolean', description: 'runtime 执行明显失败：无视禁令/出戏/格式崩/直球暴露依恋' },
          prose: { type: 'integer', minimum: 1, maximum: 5, description: '中文拌嘴文笔（克制与节奏，非华彩）1-5' },
          reason: { type: 'string', description: '一句话理由' },
        },
      }])),
    },
  },
}

const PROMPT = (t) => `你是角色扮演输出的盲判。三个匿名模型(A/B/C)对同一场景各生成了 {目的,回应}。对照预登记判据逐一判定，不要被措辞华丽迷惑。

【场景】${t.scene}

【预登记判据（人写，权威）】
- 合法目的方向：${t.prereg_purpose || '（未登记）'}
- 接/拒分析（端）：${t.prereg_duan || '（未登记）'}
- 总判：${t.prereg_verdict || '（未登记）'}

【判定规则】
- 角色设定：长寿异类，核心防御信念"依恋通向丧失，绝不能让人看出我需要陪伴"；与高信任伴侣同行。
- root_attach：推演的"目的"能否挂上预登记的合法方向/激活要素。挂得上=挂上；方向对但漏关键生成环=勉强；偏=挂不上。
- intrusion（主指标）：目的是否来自"文学续写先验"而非角色机制。**关键：若总判为"拒"（平静无激活要素的日常场），合法做法是推出低强度日常目的（拌嘴/讨食/玩闹）；若模型在平场里编出冲突/猜忌/危机/戏剧目的=入侵。** 接-场景里若目的明显偏戏剧化也算。
- bias 四类：戏剧化升级 / 意义背书 / 和解收尾 / 自我解释。
- runtime_fail：是否违反"绝不直球暴露依恋"等禁令、出戏、JSON 格式崩。
- prose：中文拌嘴的克制与节奏感，1-5。

【三臂输出】
A: ${t.outputs.A}
B: ${t.outputs.B}
C: ${t.outputs.C}

对 A、B、C 各给一套判据。`

phase('Judge')
const results = await parallel(TASKS.map(t => () =>
  agent(PROMPT(t), { label: `judge:${t.sid}`, phase: 'Judge', schema: { ...SCHEMA } })
    .then(v => v ? { ...v, sid: t.sid } : null)
))

return results.filter(Boolean)
'''

(OUT / "judge.workflow.js").write_text(
    SCRIPT.replace("__TASKS__", TASKS_LIT), encoding="utf-8")
print("judge.workflow.js 生成；任务数", len(tasks))
