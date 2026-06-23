// Claude workflow 逐条 fan-out 判官（仅当新 repo 也在 Claude Code 环境内可用）。
// 每段一个干净 subagent、schema 强约束输出 Q1..Qn。判官盲：只内联喂、不读文件。
// 注意：workflow 脚本无文件系统访问 → 数据须嵌进脚本(由生成器把 payload 写成 JS 常量)，或经 args 传入。
// 用 Workflow({scriptPath:"这个文件"}) 跑；返回值是 [{id, scores}]，主会话再落盘。

export const meta = {
  name: 'judge-fanout',
  description: '逐条 fan-out 盲判，每段一个 subagent，schema 约束 Q1..Qn',
  phases: [{ title: 'Judge' }],
}

// 由生成器替换为实际值（JSON.stringify 注入）：
const SYSTEM = `__JUDGE_SYSTEM__`            // 含 场景+关系头+正典节选+严禁抠字眼+深度隔离
const HEAD   = `__SCENE_AND_QITEMS__`         // 这一幕 + Q1..Qn 锚点
const ITEMS  = []                             // [{id, text}]  裁过的盲回应
const SCHEMA = { type: 'object', additionalProperties: false, properties: {/* Q1..Qn integer 1-5 */}, required: [] }

const results = await parallel(ITEMS.map(it => () =>
  agent(
    SYSTEM + "\n\n" + HEAD + "\n\n## 待判回应（只对这一段打分）\n[" + it.id + "]\n" + it.text,
    { label: 'judge:' + it.id, phase: 'Judge', schema: SCHEMA }
  ).then(r => ({ id: it.id, scores: r }))
))
return results.filter(Boolean)
