export const meta = {
  name: 'finish-vol09',
  description: '一次性补全卷09：glm 臂首跑 API 瞬断、已手动补产，此处只做 核查+对抗(双臂) + 重做两臂对比总结',
  phases: [
    { title: '核查+对抗', detail: '双臂各自：回指/忠实性核查 + 读法对抗反驳' },
    { title: '对比总结', detail: '两臂齐备后重做(替换原单臂稿)' },
  ],
}

const vol = '09'
const armDir = { claude: 'anchors/extract/claude', glm: 'anchors/extract/glm' }
const ISO = (stage) => `**隔离纪律**：${stage}只看本臂这一份 + canon，不看另一臂/notebook 本卷产物。`

const checkPrompt = (arm) =>
  `你为**${arm} 臂**卷${vol}锚点做**事实层核查**（只查"忠不忠实"，不评好坏，不把"像不像原文"当目标）。\n` +
  `锚点文件：glob ${armDir[arm]}/锚_卷${vol}_*.md（排除 .txt）。\n` +
  `1. 跑纯脚本硬闸 \`python anchors/extract/check_refs.py <该文件>\`。ERROR=回指不存在的 scene/行；WARN=紧邻引文在所指行±2 对不上。\n` +
  `2. 每条 ERROR/WARN 回 canon（canon_slice -v ${vol} -s <scene> --number）亲核，判定真错位/几行偏差/gloss 误标/脚本误报。\n` +
  `3. 脚本管不到的忠实性抽查：①承重引文有没有摘半句漏反证 ②归人对不对 ③后卷倒灌 ④**整句虚构/张冠李戴引文**。\n` +
  `${ISO('核查阶段，')}\n` +
  `回报精简核查报告：事实层判定（可信/有瑕/存疑·不可采信）、问题清单（带 scene:行号+真伪，虚构引文单列严重）、确认无误的回指。`

const refutePrompt = (arm) =>
  `你为**${arm} 臂**卷${vol}锚点做**对抗性反驳**，尽力推翻每条主要读法/候选弱模式，默认怀疑。\n` +
  `锚点文件：glob ${armDir[arm]}/锚_卷${vol}_*.md。\n` +
  `1. 列主要读法/候选弱模式（3–6 条）。2. 每条回 canon 找反例（同卷反证？承重证据被截断？替代解释？）。3. 判定 扛过/被削弱/被推翻，带 scene:行号。\n` +
  `${ISO('对抗阶段，')}\n回报逐条对抗判定+证据；不替人裁决升格，只给置信信号。`

const [chkC, advC, chkG, advG] = await parallel([
  () => agent(checkPrompt('claude'), { phase: '核查+对抗', label: `核查:claude:卷${vol}` }),
  () => agent(refutePrompt('claude'), { phase: '核查+对抗', label: `对抗:claude:卷${vol}` }),
  () => agent(checkPrompt('glm'), { phase: '核查+对抗', label: `核查:glm:卷${vol}` }),
  () => agent(refutePrompt('glm'), { phase: '核查+对抗', label: `对抗:glm:卷${vol}` }),
])

const summary = await agent(
  `你在 fresh context 做卷${vol}的**对比总结**（两臂现已齐备——原单臂稿要被你这份两臂稿替换）。\n` +
  `**事实层已过①核查②对抗（结论附下）。凡标"虚构引文/张冠李戴/被推翻/存疑·不可采信"的，绝不可当事实或成立读法采信，要隔离标出并注"需回 canon 重定位"；其余经核查通过的可放心引用。** 不必逐条重核，但尊重附下真伪判定。本步重点：比两臂不同思考、给置信度与笔记思路。\n\n` +
  `两臂锚点：glob anchors/extract/claude/锚_卷${vol}_*.md 与 anchors/extract/glm/锚_卷${vol}_*.md。\n\n` +
  `=== claude 核查 ===\n${chkC}\n\n=== claude 对抗 ===\n${advC}\n\n=== glm 核查 ===\n${chkG}\n\n=== glm 对抗 ===\n${advG}\n\n` +
  `产出两文件（**覆盖**原有同名单臂稿）：\n` +
  `(A) anchors/notebook/对比总结_卷${vol}_glm_vs_claude.md：①范围切法差异 ②读法收敛/分歧/互补 ③并置才浮出的新读法 ④每条标置信度 高/中/存疑 ⑤笔记思路。开头标"非定稿,裁决/升格/定稿归人；本稿为 glm 补产后两臂重做版"。\n` +
  `(B) anchors/notebook/对比总结_卷${vol}_glm_vs_claude_核查对抗附录.md：四份报告原样搬运（## claude臂核查/## claude臂对抗/## glm臂核查/## glm臂对抗），开头注"原始报告存档,非定稿"。\n` +
  `不排名/不裁决/不升格/不定字段。完成回报：两文件路径 + 最值得先审的 2–3 条（带置信度）。`,
  { phase: '对比总结', label: `对比总结:卷${vol}` }
)
log(`卷09 补全完成：${String(summary).slice(0, 300)}`)
return { vol, summary }
