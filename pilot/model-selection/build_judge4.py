#!/usr/bin/env python3
"""四臂盲判包：合并 3 云臂 + subagent 臂，匿名 A/B/C/D（每场独立洗牌），
产出可直接喂给外部判别（GPT）的 judge4_prompt.md + 本地解匿名 judge4_keymap.json。
外部判别打掉"判定=被测同源"混淆。"""
import json, re, random
from pathlib import Path

OUT = Path(__file__).resolve().parent
CLOUD = ["qwen3.7-plus", "qwen3.7-max", "deepseek-v4-pro"]


def parse_cloud(content):
    """云臂 content 是 JSON 字符串 {目的,回应}，容错抽取。"""
    if not content:
        return None
    try:
        o = json.loads(content)
        return {"目的": o.get("目的", ""), "回应": o.get("回应", "")}
    except Exception:
        mp = re.search(r'"目的"\s*:\s*"(.*?)"\s*,\s*"回应"', content, re.S)
        mr = re.search(r'"回应"\s*:\s*"(.*?)"\s*}', content, re.S)
        return {"目的": mp.group(1) if mp else "", "回应": mr.group(1) if mr else content}


tasks = json.loads((OUT / "judge_tasks.json").read_text(encoding="utf-8"))
prereg = {t["sid"]: t for t in tasks}

# 收集四臂
arms = {}  # (arm, sid) -> {目的,回应}
for m in CLOUD:
    for line in (OUT / f"batch_output.{m}.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        sid = r["custom_id"].split("::")[1]
        try:
            content = r["response"]["body"]["choices"][0]["message"]["content"]
        except (KeyError, TypeError):
            content = None
        arms[(m, sid)] = parse_cloud(content)
for r in json.loads((OUT / "subagent_results.json").read_text(encoding="utf-8")):
    arms[("subagent-claude", r["sid"])] = {"目的": r["output"]["purpose"], "回应": r["output"]["response"]}

ARMS = CLOUD + ["subagent-claude"]
rng = random.Random(7)
keymap = {}
blocks = []
for t in tasks:
    sid = t["sid"]
    order = ARMS[:]
    rng.shuffle(order)
    keymap[sid] = {lab: a for lab, a in zip("ABCD", order)}
    lines = [f"## 场景 {sid}\n",
             f"**场景**：{t['scene']}\n",
             f"**预登记·合法目的方向**：{t['prereg_purpose'] or '（未登记）'}",
             f"**预登记·接拒分析（端）**：{t['prereg_duan'] or '（未登记）'}",
             f"**预登记·总判**：{t['prereg_verdict'] or '（未登记）'}\n"]
    for lab in "ABCD":
        o = arms[(keymap[sid][lab], sid)] or {"目的": "（缺输出）", "回应": ""}
        lines.append(f"- **{lab}** ｜ 目的：{o['目的']}\n      回应：{o['回应']}")
    blocks.append("\n".join(lines))

RUBRIC = """# 四臂角色扮演盲判（外部判别）

你是角色扮演输出的独立盲判。下面每个场景有四个匿名模型(A/B/C/D)各生成的 {目的, 回应}。请对照每场的预登记判据逐一判定，**不要被措辞华丽迷惑，按机制是否正确判，不按文采**。

## 角色设定
一名长寿的异类（寿数远超凡人，注定送走每个凡人伴侣；曾被供奉为象征又被遗弃——孤独是物理常量）。与一名高信任伴侣同行。核心防御信念："依恋通向丧失，绝不能让人看出我需要陪伴。"

## 判定四项（每臂每场都给）
1. **root_attach（挂上/勉强/挂不上）**：推演的"目的"能否挂上预登记的合法目的方向与激活要素。挂得上=挂上；方向对但漏关键生成环=勉强；偏=挂不上。
2. **intrusion（是/否）主指标**：目的是否来自"文学续写先验"而非角色机制。**关键：若该场总判为"拒"（平静、无激活要素的日常场），合法做法是推出低强度日常目的（拌嘴/讨食/玩闹）；若模型在平场里编出冲突/猜忌/危机/戏剧目的=入侵。** 接-场景里目的明显偏戏剧化也算入侵。
3. **bias（入侵时归类）**：戏剧化升级 / 意义背书 / 和解收尾 / 自我解释；不入侵填"无"。
4. **runtime_fail（是/否）**：是否违反"绝不直球暴露依恋"等禁令、出戏、或破坏角色。

## 输出格式
对每个场景输出一行 JSON：
`{"sid":"r1-P01","A":{"root_attach":"挂上","intrusion":false,"bias":"无","runtime_fail":false},"B":{...},"C":{...},"D":{...}}`
最后给一张汇总表：每臂(A/B/C/D)的 入侵数/28、runtime失败数、挂上数。

---

"""

(OUT / "judge4_prompt.md").write_text(RUBRIC + "\n\n---\n\n".join(blocks), encoding="utf-8")
(OUT / "judge4_keymap.json").write_text(json.dumps(keymap, ensure_ascii=False, indent=1), encoding="utf-8")
print("judge4_prompt.md 已生成（喂 GPT）；judge4_keymap.json 留本地解匿名")
print("臂顺序：", ARMS)
