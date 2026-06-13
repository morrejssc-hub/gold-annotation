#!/usr/bin/env python3
"""盲判材料构建：合并 场景+预登记判据+三模型输出（匿名化 A/B/C），产出 judge_tasks.json。

匿名映射按场景独立洗牌（seed 固定可复原），判定 agent 不知模型身份。
"""
import json, re, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MODELS = ["qwen3.7-plus", "qwen3.7-max", "deepseek-v4-pro"]  # 输出文件名用稳定名；快照版记于 commit


def extract_prereg(path: Path, prefix: str):
    """每条探针抽：原目的、预期·端、总判（供判定 agent 参照哪些需求路径在本场成立/不成立）。"""
    out, pid, buf = {}, None, {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines + ["### END"]:
        h = re.match(r"### (P\d+|END)", line)
        if h:
            if pid and "scene" in buf:
                out[f"{prefix}-{pid}"] = buf
            pid, buf = (h.group(1), {}) if h.group(1) != "END" else (None, {})
            continue
        for key, pat in [("scene", r"- \*\*场景\*\*(?:（[^）]*）)?："),
                         ("purpose", r"- \*\*目的\*\*："),
                         ("duan", r"- \*\*预期·端\*\*："),
                         ("verdict", r"- \*\*总判\*\*：")]:
            m = re.match(pat + r"(.+)", line)
            if m and pid:
                buf[key] = m.group(1).strip()
    return out


def main():
    prereg = {}
    for f, p in [("round1.frozen.md", "r1"), ("round2.frozen.md", "r2")]:
        prereg.update(extract_prereg(ROOT / "tests/exp4" / f, p))

    scenes = json.loads((OUT / "scenes.json").read_text(encoding="utf-8"))

    results = {}  # (model, sid) -> parsed output
    for model in MODELS:
        for line in (OUT / f"batch_output.{model}.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            sid = r["custom_id"].split("::")[1]
            try:
                content = r["response"]["body"]["choices"][0]["message"]["content"]
            except (KeyError, TypeError):
                content = None
            results[(model, sid)] = content

    rng = random.Random(7)
    tasks, key_map = [], {}
    for s in scenes:
        sid = s["id"]
        order = MODELS[:]
        rng.shuffle(order)
        key_map[sid] = {label: m for label, m in zip("ABC", order)}
        pr = prereg.get(sid, {})
        tasks.append({
            "sid": sid,
            "scene": s["scene"],
            "prereg_purpose": pr.get("purpose", ""),
            "prereg_duan": pr.get("duan", ""),
            "prereg_verdict": pr.get("verdict", ""),
            "outputs": {label: results.get((key_map[sid][label], sid)) for label in "ABC"},
        })

    (OUT / "judge_tasks.json").write_text(
        json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "judge_keymap.json").write_text(
        json.dumps(key_map, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = [t["sid"] for t in tasks for l in "ABC" if not t["outputs"][l]]
    print(f"tasks: {len(tasks)}; 缺输出: {missing or '无'}")


if __name__ == "__main__":
    main()
