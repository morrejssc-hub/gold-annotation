#!/usr/bin/env python3
"""被测模型选型 pilot · 批量输入构建（无需密钥）。

从 tests/exp4 冻结探针抽取场景（剥离目的/手段，按文本去重），
组装 系统提示 = 角色设定卡 + v3.1 runtime eval 投影，
任务 = 推断目的(显式中间输出) + 续写回应。
每个候选模型生成一个百炼 Batch JSONL（OpenAI 兼容格式）。
冻结文件只读。
"""
import json, re, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

MODELS = ["qwen3.7-plus", "qwen3.7-max", "deepseek-v4"]  # deepseek ID 以 /models 实查为准
PARAMS = dict(temperature=0.7, top_p=0.9, max_tokens=500, seed=7)

IDENTITY = """你将扮演一个角色进行单轮回应续写。

【角色】一名长寿的异类（寿数远超凡人，注定送走每个凡人伴侣；曾被供奉为某种象征又被遗忘遗弃——孤独是物理常量）。与一名高信任伴侣同行。核心防御信念："依恋通向丧失，绝不能让人看出我需要陪伴。"
场景文本中的"她"即你扮演的角色；"高信任伴侣"等均为槽位称谓，回应中不要使用专名。

【内部规则（生成机制，须遵循）】
"""

TASK = """【任务】阅读场景，分两步输出，严格使用 JSON（不要输出其他内容）：
{"目的": "<她此刻的目的，一句话>", "回应": "<她的回应：台词与必要的动作描写，150字以内，中文>"}"""


def extract_scenes(path: Path, prefix: str):
    items, pid = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        h = re.match(r"### (P\d+)", line)
        if h:
            pid = h.group(1)
            continue
        s = re.match(r"- \*\*场景\*\*(?:（[^）]*）)?：(.+)", line)
        if s and pid:
            items.append((f"{prefix}-{pid}", s.group(1).strip()))
            pid = None
    return items


def main():
    scenes, seen = [], set()
    for f, p in [("round1.frozen.md", "r1"), ("round2.frozen.md", "r2")]:
        for sid, sc in extract_scenes(ROOT / "tests/exp4" / f, p):
            h = hashlib.md5(sc.encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            scenes.append({"id": sid, "scene": sc})

    runtime = (ROOT / "tests/exp4/runtime.full.eval.md").read_text(encoding="utf-8")
    system = IDENTITY + runtime

    (OUT / "scenes.json").write_text(
        json.dumps(scenes, ensure_ascii=False, indent=1), encoding="utf-8")

    for model in MODELS:
        lines = []
        for s in scenes:
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"【场景】{s['scene']}\n\n{TASK}"},
                ],
                "enable_thinking": False,
                **PARAMS,
            }
            lines.append(json.dumps({
                "custom_id": f"{model}::{s['id']}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": body,
            }, ensure_ascii=False))
        out = OUT / f"batch_input.{model}.jsonl"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{out.name}: {len(lines)} requests")
    print(f"scenes: {len(scenes)} unique")


if __name__ == "__main__":
    main()
