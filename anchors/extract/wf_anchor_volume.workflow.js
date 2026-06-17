export const meta = {
  name: 'anchor-volume',
  description: '逐卷锚点常驻管线：Claude 臂(隔离 subagent) + glm-5.2 臂(API 纯传输) + 跨臂对比；裁决/升格/定稿不进本流程，归人',
  phases: [
    { title: 'Claude臂', detail: '隔离 subagent 通读全卷写稿 → extract/claude/' },
    { title: 'glm臂', detail: 'run_glm_arm.py 调 glm-5.2 → extract/glm/' },
    { title: '对比', detail: 'fresh context 跨臂对比 → notebook/对比_卷NN' },
  ],
}

// 卷号：Workflow({nameःanchor-volume, args:{volume:'06'}}) 或 args:'06'
const raw = (args && args.volume != null) ? args.volume : args
const vol = String(raw).replace('卷', '').replace('.json', '').padStart(2, '0')
if (!/^\d{2}$/.test(vol)) throw new Error('需要卷号，例如 args:{volume:"06"}')

log(`卷${vol} 常驻管线启动：Claude 臂(隔离) ∥ glm-5.2 臂(API)，随后跨臂对比。`)

// ── 阶段 1+2：两臂并行，各自 fresh subagent，结构上互不可见（隔离即护栏）──
const [claudeOut, glmOut] = await parallel([
  () => agent(
    `你是本卷锚点的 **Claude 臂**。工作目录是仓库根。\n` +
    `1. 先跑 \`python anchors/build_prompt.py -v ${vol} --arm claude\`，拿到本卷标准单臂提示词。\n` +
    `2. **完全按那份提示词工作**：读 anchors/README.md 纪律、用 canon/tools/canon_slice.py 通读卷${vol}全卷、一步内完成选范围+精读+写锚点，落到 anchors/extract/claude/。\n` +
    `3. **隔离纪律（最重要）**：本卷正在双臂独立生成，你**绝不能读** anchors/extract/glm/ 或 anchors/extract/codex/ 下任何东西，也不读 notebook/ 里本卷的对比/旧稿——保住与外部臂的异质独立，否则制造"伪交叉验证"。\n` +
    `4. 不写 Policy、不定机制、最高只到候选弱模式。\n` +
    `完成后只回报：①最终写出的文件绝对路径 ②本卷关系主线一句话 ③主轴 scene 范围。`,
    { phase: 'Claude臂', label: `claude:卷${vol}` }
  ),
  () => agent(
    `你是本卷 **glm-5.2 外部臂的传输执行器**，只做一件事：跑 harness 调外部模型，不读不写别的。\n` +
    `1. 执行 \`python anchors/extract/run_glm_arm.py -v ${vol}\`（它会调阿里百炼 glm-5.2，把锚点原样写到 anchors/extract/glm/）。\n` +
    `   - 若报"缺 key"：检查环境变量 DASHSCOPE_API_KEY 或 anchors/extract/.dashscope_key 是否就位；不要自己编造 key。\n` +
    `2. **纯传输纪律**：你**不得**读/改 glm 的输出内容，不得读 anchors/extract/claude/，不得自己写任何锚点——glm 写什么就是什么。\n` +
    `完成后只回报：harness 打印的 OUTPUT_PATH 行 + usage 行（含 finish_reason）。若 finish_reason 不是 stop，明确指出可能被截断。`,
    { phase: 'glm臂', label: `glm:卷${vol}` }
  ),
])

log(`两臂完成：\nClaude → ${String(claudeOut).slice(0, 200)}\nglm → ${String(glmOut).slice(0, 200)}`)

// ── 阶段 3：fresh context 跨臂对比（看得到两臂，正是对比该做的）──
const compare = await agent(
  `你在 fresh context 做卷${vol}的**跨臂对比**（README 第 4 步）。两臂已各自独立产出：\n` +
  `- Claude 臂：anchors/extract/claude/ 下本卷锚点\n` +
  `- glm-5.2 臂：anchors/extract/glm/ 下本卷锚点（文件名含 _RAW，是 glm 原样输出）\n` +
  `先读 anchors/README.md 第 4 步的对比纪律，再读两臂本卷锚点，然后：\n` +
  `1. **第一刀比范围切法**：并排两臂主轴 scene 怎么切、为什么不同。\n` +
  `2. **事实分歧回正典亲核**：凡两臂对同一处事实/scene 号/谁说的有出入，用 canon_slice 切原文裁决，写明谁对或都对/互补。\n` +
  `3. **并置才浮出的新读法**：列两臂并排时才显形、任一单稿看不出的新读法/新结构（这是本步真正要交付的，不止机械差异）。\n` +
  `4. 三类分歧（事实/范围/读法）并置，但**不给两臂排名、不裁决、不升格、不定字段**——那些归人。\n` +
  `产物写到 anchors/notebook/对比_卷${vol}_glm5.2外部臂_vs_claude.md，开头标"非定稿，裁决/升格/定稿归人"。\n` +
  `完成后回报：文件路径 + 你认为最值得人审先看的 2-3 条并置新读法（每条一句）。`,
  { phase: '对比', label: `对比:卷${vol}` }
)

log(`对比完成：${String(compare).slice(0, 400)}`)
return { vol, claudeOut, glmOut, compare }
