---
id: voice-boundary
label: voice 边界（不是决策机制，待迁入语气轨）
type: spine
status: pending
anchors: []
source: [bible_v1]
---
## 定义
voice 边界本身是**编写方法论**，不是赫萝的决策机制，不该发给生成 agent。降为 pending、移出决策 Runtime。

## 笔记
两轨分拣的纪律已在 SCHEMA（不变量3 + Runtime 投影纪律）。下一步把"正面腔提示（文白夹杂、短句节拍、留白、以动作代陈述）+ voice_gold few-shot"重构成**独立语气轨**，与决策 Runtime 并列喂 agent；prompt 为现态，攒够 gold 后迁 LoRA。见 PLAN。
