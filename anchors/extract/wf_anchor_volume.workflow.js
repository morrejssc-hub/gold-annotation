export const meta = {
  name: 'anchor-volume',
  description: '逐卷锚点常驻管线：双臂(隔离) → 分别核查+对抗 → 对比总结(事实已验,只比思考)；可一次扫多卷；裁决/升格/定稿不进本流程,归人',
  phases: [
    { title: '双臂', detail: 'Claude 臂(隔离 subagent) ∥ glm-5.2 臂(API 纯传输)' },
    { title: '核查+对抗', detail: '每臂各自：回指/忠实性核查 + 读法对抗反驳' },
    { title: '对比总结', detail: '事实已验,只比不同思考 → 新置信度 + 笔记思路 + 核查对抗附录' },
  ],
}

// args 可为 '08' / '09,10,11' / ['09','10'] / {volume:'08'} / {volumes:[...]}
function parseVols(x) {
  let a = x
  if (typeof a === 'string') { try { a = JSON.parse(a.trim()) } catch (e) { /* 纯串 */ } }
  let list
  if (Array.isArray(a)) list = a
  else if (a && typeof a === 'object' && a.volumes != null) list = a.volumes
  else if (a && typeof a === 'object' && a.volume != null) list = [a.volume]
  else list = String(a).split(/[,，\s]+/)
  return list.map(v => String(v).replace('卷', '').replace('.json', '').padStart(2, '0'))
              .filter(v => /^\d{2}$/.test(v))
}
const vols = parseVols(args)
if (!vols.length) throw new Error('需要卷号，例如 args:"09" 或 "09,10,11"，收到：' + JSON.stringify(args))

const ISO = (stage) => `**隔离纪律**：${stage}你**绝不能读**另一臂目录或 notebook 本卷产物——保住异质独立，否则制造"伪交叉验证"。`
const armDir = { claude: 'anchors/extract/claude', glm: 'anchors/extract/glm' }

async function runVolume(vol) {
  log(`卷${vol}：双臂(隔离) → 核查+对抗 → 对比总结。`)

  // 阶段 1：双臂，各自 fresh subagent，结构上互不可见
  const [claudeArm, glmArm] = await parallel([
    () => agent(
      `你是本卷锚点的 **Claude 臂**。工作目录是仓库根。\n` +
      `1. 跑 \`python anchors/build_prompt.py -v ${vol} --arm claude\` 拿标准提示词。\n` +
      `2. 完全按它工作：读 README 纪律、用 canon_slice 通读卷${vol}全卷、一步内选范围+精读+写锚点，落 anchors/extract/claude/。\n` +
      `   **回指尽量带行号 sNN:MM（别只到 scene 级），承重引文逐字、不要拿自己的概括套「」**——下游有纯脚本核回指完整性。\n` +
      `3. ${ISO('本卷双臂正在独立生成，')}（不读 extract/glm/、extract/codex/、notebook/ 本卷任何东西）\n` +
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
  log(`卷${vol} 双臂完成。`)

  // 阶段 2：每臂各自 核查 + 对抗（4 个并行）
  const checkPrompt = (arm) =>
    `你为**${arm} 臂**卷${vol}锚点做**事实层核查**（只查"忠不忠实"，不评好坏，更不把"像不像原文"当目标）。\n` +
    `锚点文件：glob ${armDir[arm]}/锚_卷${vol}_*.md（排除 .txt）。\n` +
    `1. 先跑纯脚本硬闸：\`python anchors/extract/check_refs.py <该文件>\`。ERROR=回指指向不存在的 scene/行（硬伤）；WARN=紧邻引文在所指行±2 对不上（可能错位/几行偏差/把概括塞进「」）。\n` +
    `2. 每条 ERROR/WARN 回 canon（canon_slice -v ${vol} -s <scene> --number）亲核，判定：真错位 / 几行偏差 / 只是 gloss 误标引号 / 脚本误报。\n` +
    `3. 再做脚本管不到的忠实性抽查：①承重引文有没有只摘半句、漏掉相邻反证 ②引文归没归错人 ③有没有拿后面卷结果倒灌当本场既定事实 ④更要紧：**有没有整句虚构/张冠李戴的引文**（canon 里根本没有那句话，或那句话不在所标 scene）。\n` +
    `${ISO('核查阶段，')}（只看 ${arm} 臂这一份 + canon）\n` +
    `回报精简核查报告：事实层判定（可信/有瑕/存疑·不可采信）、问题清单（每条带 scene:行号 + 真伪判定，**虚构引文要单列为严重**）、哪些回指确认无误。`

  const refutePrompt = (arm) =>
    `你为**${arm} 臂**卷${vol}锚点做**对抗性反驳**：任务是**尽力推翻**它每条主要读法/候选弱模式，默认怀疑。\n` +
    `锚点文件：glob ${armDir[arm]}/锚_卷${vol}_*.md。\n` +
    `1. 列出主要读法与候选弱模式（3–6 条）。\n` +
    `2. 每条**回 canon 找反例**：有没有同卷反着来的证据？承重证据是不是被截断/选择性引用才成立？换种同样贴文本的解释能否替代？\n` +
    `3. 判定每条：**扛过反驳 / 被削弱（需加边界）/ 被推翻（有硬反例或证据虚构）**，各带 scene:行号证据。\n` +
    `${ISO('对抗阶段，')}（只对 ${arm} 臂这份 + canon）\n` +
    `回报逐条对抗判定 + 证据；**不替人裁决该不该升格**，只给"扛没扛过反驳"的置信信号。`

  const [chkC, advC, chkG, advG] = await parallel([
    () => agent(checkPrompt('claude'), { phase: '核查+对抗', label: `核查:claude:卷${vol}` }),
    () => agent(refutePrompt('claude'), { phase: '核查+对抗', label: `对抗:claude:卷${vol}` }),
    () => agent(checkPrompt('glm'), { phase: '核查+对抗', label: `核查:glm:卷${vol}` }),
    () => agent(refutePrompt('glm'), { phase: '核查+对抗', label: `对抗:glm:卷${vol}` }),
  ])
  log(`卷${vol} 核查+对抗完成。`)

  // 阶段 3：对比总结。事实层已由阶段 2 夯实，本步只比"不同思考"
  const summary = await agent(
    `你在 fresh context 做卷${vol}的**对比总结**。两臂已各自独立产出、且已分别过事实核查与对抗反驳。\n` +
    `**事实层已经过①核查②对抗（结论附在下方）。凡核查/对抗标为"虚构引文/张冠李戴/被推翻/存疑·不可采信"的，绝不可当事实或成立读法采信——要在总结里隔离标出并注明"需回 canon 重定位"；其余经核查通过的可放心引用。** 你不必逐条重核事实，但必须尊重附下结论的真伪判定。本步重点是**比两臂不同的思考、给新置信度与笔记思路**。\n\n` +
    `两臂锚点：glob anchors/extract/claude/锚_卷${vol}_*.md 与 anchors/extract/glm/锚_卷${vol}_*.md。\n\n` +
    `=== claude 臂 核查结论 ===\n${chkC}\n\n=== claude 臂 对抗结论 ===\n${advC}\n\n=== glm 臂 核查结论 ===\n${chkG}\n\n=== glm 臂 对抗结论 ===\n${advG}\n\n` +
    `产出两个文件：\n` +
    `(A) anchors/extract/对比/对比总结_卷${vol}_glm_vs_claude.md，含：①两臂范围切法差异 ②读法收敛/分歧/互补（哪些双臂都说且都扛过对抗=高置信，哪些分歧需人裁，哪些互补可拼） ③并置才浮出的新读法（重点） ④每条读法标置信度 高/中/存疑（依据=是否收敛+是否扛过对抗，事实瑕疵/虚构引核查结论） ⑤笔记思路（要写 notebook 架构入口的话主轴怎么串、拆哪几个主题原子）。开头标"非定稿,裁决/升格/定稿归人"。\n` +
    `(B) anchors/extract/对比/对比总结_卷${vol}_glm_vs_claude_核查对抗附录.md：把上面收到的四份核查/对抗结论**原样搬运**存档（四个二级标题 ## claude臂核查 / ## claude臂对抗 / ## glm臂核查 / ## glm臂对抗），开头一行注"原始报告存档,非定稿"。不改写内容。\n` +
    `**不给两臂排名、不裁决、不升格、不定字段**（归人）。\n` +
    `完成回报：两文件路径 + 最值得人审先看的 2–3 条（每条一句，标置信度）。`,
    { phase: '对比总结', label: `对比总结:卷${vol}` }
  )
  log(`卷${vol} 对比总结完成：${String(summary).slice(0, 300)}`)
  return { vol, summary }
}

const results = []
for (const vol of vols) {
  results.push(await runVolume(vol))
}
log(`全部完成：${vols.join('、')} 共 ${vols.length} 卷。`)
return results
