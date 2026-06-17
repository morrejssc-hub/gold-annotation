export const meta = {
  name: 'anchor-volume',
  description: '逐卷锚点常驻管线：双臂(隔离) → 分别核查+对抗 → 对比总结(事实已验,只比思考)；裁决/升格/定稿不进本流程,归人',
  phases: [
    { title: '双臂', detail: 'Claude 臂(隔离 subagent) ∥ glm-5.2 臂(API 纯传输)' },
    { title: '核查+对抗', detail: '每臂各自：回指/忠实性核查 + 读法对抗反驳' },
    { title: '对比总结', detail: '事实已验,只比不同思考 → 新置信度 + 笔记思路' },
  ],
}

// 卷号：args 可为 {volume:'08'} / JSON 串 / 纯串 '08' / '8'
let a = args
if (typeof a === 'string') { try { a = JSON.parse(a.trim()) } catch (e) { /* 留作纯串 */ } }
const raw = (a && typeof a === 'object' && a.volume != null) ? a.volume : a
const vol = String(raw).replace('卷', '').replace('.json', '').padStart(2, '0')
if (!/^\d{2}$/.test(vol)) throw new Error('需要卷号，例如 args:"08"，收到：' + JSON.stringify(args))

const ISOLATION = `**隔离纪律**：本卷双臂正在独立生成，你**绝不能读**另一臂目录或 notebook 本卷产物——保住异质独立，否则制造"伪交叉验证"。`

log(`卷${vol} 常驻管线：双臂(隔离) → 核查+对抗 → 对比总结。`)

// ── 阶段 1：双臂，各自 fresh subagent，结构上互不可见 ──
const [claudeArm, glmArm] = await parallel([
  () => agent(
    `你是本卷锚点的 **Claude 臂**。工作目录是仓库根。\n` +
    `1. 跑 \`python anchors/build_prompt.py -v ${vol} --arm claude\` 拿标准提示词。\n` +
    `2. 完全按它工作：读 README 纪律、用 canon_slice 通读卷${vol}全卷、一步内选范围+精读+写锚点，落 anchors/extract/claude/。\n` +
    `   **回指尽量带行号 sNN:MM（不要只到 scene 级），承重引文务必逐字、不要拿自己的概括套「」**——下游有纯脚本核回指完整性。\n` +
    `3. ${ISOLATION}（不读 extract/glm/、extract/codex/、notebook/ 本卷任何东西）\n` +
    `4. 不写 Policy、最高到候选弱模式。\n` +
    `完成只回报：写出文件名、本卷关系主线一句话、主轴 scene 范围。`,
    { phase: '双臂', label: `claude:卷${vol}` }
  ),
  () => agent(
    `你是本卷 **glm-5.2 外部臂的传输执行器**，只跑 harness、不读不写别的。\n` +
    `1. 执行 \`python anchors/extract/run_glm_arm.py -v ${vol}\`（调 glm-5.2，原样写到 anchors/extract/glm/）。报"缺 key"就查 DASHSCOPE_API_KEY 或 anchors/extract/.dashscope_key，别编 key。\n` +
    `2. **纯传输**：不读/改 glm 输出，不读 extract/claude/，不自己写锚点。\n` +
    `完成只回报：OUTPUT_PATH 行 + usage 行（含 finish_reason；非 stop 要点出可能截断）。`,
    { phase: '双臂', label: `glm:卷${vol}` }
  ),
])
log(`双臂完成。\nclaude → ${String(claudeArm).slice(0, 160)}\nglm → ${String(glmArm).slice(0, 160)}`)

// ── 阶段 2：每臂各自 核查 + 对抗（4 个并行，互不依赖）──
const armDir = { claude: 'anchors/extract/claude', glm: 'anchors/extract/glm' }
const checkPrompt = (arm) =>
  `你为**${arm} 臂**卷${vol}锚点做**事实层核查**（只查"忠不忠实"，不评好坏，更不把"像不像原文"当目标）。\n` +
  `锚点文件：用 glob 找 ${armDir[arm]}/锚_卷${vol}_*.md（排除 .txt）。\n` +
  `1. 先跑纯脚本硬闸：\`python anchors/extract/check_refs.py <该文件>\`。ERROR=回指指向不存在的 scene/行（硬伤）；WARN=紧邻引文在所指行±2 对不上（可能错位/几行偏差/把概括塞进「」）。\n` +
  `2. 对每条 ERROR/WARN 回 canon（canon_slice -v ${vol} -s <scene> --number）亲核，判定：真错位 / 几行偏差 / 只是 gloss 误标引号 / 脚本误报。\n` +
  `3. 再做脚本管不到的忠实性抽查：①承重引文有没有只摘半句、漏掉相邻反证 ②引文归没归错人 ③有没有拿后面卷结果倒灌当本场既定事实 ④声明"只读梗概"的 scene 有没有被悄悄整段漏。\n` +
  `${ISOLATION.replace('双臂正在独立生成', '核查阶段')}（只看 ${arm} 臂这一份 + canon，不看另一臂、不看 notebook）\n` +
  `回报一份精简核查报告：事实层是否扎实（可信/有瑕/存疑）、问题清单（每条带 scene:行号 + 真伪判定）、哪些回指/引文确认无误。`

const refutePrompt = (arm) =>
  `你为**${arm} 臂**卷${vol}锚点做**对抗性反驳**：你的任务是**尽力推翻**它的每条主要读法/候选弱模式，默认怀疑。\n` +
  `锚点文件：glob ${armDir[arm]}/锚_卷${vol}_*.md。\n` +
  `1. 列出它的主要读法与候选弱模式（3–6 条）。\n` +
  `2. 对每条**回 canon 找反例**：有没有同卷场景反着来的证据？承重证据是不是被截断/选择性引用才成立？换一种同样贴文本的解释能不能替代它？\n` +
  `3. 判定每条：**扛过反驳（给不出反例）/ 被削弱（有局部反例，需加边界）/ 被推翻（有硬反例）**，各带 scene:行号证据。\n` +
  `${ISOLATION.replace('双臂正在独立生成', '对抗阶段')}（只对 ${arm} 臂这份 + canon，不看另一臂）\n` +
  `回报：逐条读法的对抗判定 + 证据；**不替人裁决该不该升格**，只给"扛没扛过反驳"的置信信号。`

const [chkC, advC, chkG, advG] = await parallel([
  () => agent(checkPrompt('claude'), { phase: '核查+对抗', label: `核查:claude:卷${vol}` }),
  () => agent(refutePrompt('claude'), { phase: '核查+对抗', label: `对抗:claude:卷${vol}` }),
  () => agent(checkPrompt('glm'), { phase: '核查+对抗', label: `核查:glm:卷${vol}` }),
  () => agent(refutePrompt('glm'), { phase: '核查+对抗', label: `对抗:glm:卷${vol}` }),
])
log(`核查+对抗完成（claude/glm 各一组）。`)

// ── 阶段 3：对比总结。事实层已由阶段 2 夯实，这步只比"不同思考" ──
const summary = await agent(
  `你在 fresh context 做卷${vol}的**对比总结**。两臂已各自独立产出、且已分别过事实核查与对抗反驳——\n` +
  `**事实层就当已经验证正确**（核查/对抗结论附在下方），你**不必再当事实裁判**；这步只做一件事：**比两臂不同的思考，得出新的置信度与笔记思路**。\n\n` +
  `两臂锚点：glob anchors/extract/claude/锚_卷${vol}_*.md 与 anchors/extract/glm/锚_卷${vol}_*.md。\n\n` +
  `=== claude 臂 核查结论 ===\n${chkC}\n\n=== claude 臂 对抗结论 ===\n${advC}\n\n=== glm 臂 核查结论 ===\n${chkG}\n\n=== glm 臂 对抗结论 ===\n${advG}\n\n` +
  `据此写一份对比总结到 anchors/notebook/对比总结_卷${vol}_glm_vs_claude.md，含：\n` +
  `1. **两臂范围切法差异**（一刀并排）。\n` +
  `2. **读法：收敛 / 分歧 / 互补**——哪些两臂都说且都扛过对抗（**置信度高**）、哪些分歧需人裁、哪些互补能拼成更完整的一条。\n` +
  `3. **并置才浮出的新读法**（任一单稿看不出的，本步重点）。\n` +
  `4. **置信度标注**：每条读法标 高/中/存疑（依据＝是否收敛 + 是否扛过对抗，事实瑕疵引核查结论）。\n` +
  `5. **笔记思路**：若要写 notebook 架构入口，主轴该怎么串、拆哪几个主题原子。\n` +
  `**不给两臂排名、不裁决、不升格、不定字段**（归人）。开头标"非定稿,裁决/升格/定稿归人"。\n` +
  `完成回报：文件路径 + 最值得人审先看的 2–3 条（每条一句，标置信度）。`,
  { phase: '对比总结', label: `对比总结:卷${vol}` }
)
log(`对比总结完成：${String(summary).slice(0, 400)}`)
return { vol, claudeArm, glmArm, chkC, advC, chkG, advG, summary }
