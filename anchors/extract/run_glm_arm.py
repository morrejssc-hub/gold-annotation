#!/usr/bin/env python3
"""逐卷跑「外部真模型臂」（glm-5.2，经阿里百炼 API 直调，非 subagent）的传输 harness。

定位：**纯传输**——把 build_prompt.py 的标准单臂提示词 + README（方法）
+ 一份**更早卷**的格式样例 + 目标卷全卷正文，原样喂给 glm-5.2，再把模型写的锚点原样落盘到
`anchors/extract/glm/`。不注入任何读法，保住该臂相对 Claude 臂的独立异质对比。

GLM 经 API 直调没有工具/文件系统，无法自己跑 canon_slice、无法写文件，故由本脚本代为：
切片整卷并内联正文（视同它已通读整卷）、内联 README 与格式样例，它在回复正文里直接吐锚点 markdown。

key 从环境变量 `DASHSCOPE_API_KEY` 读；没有则回退读 gitignore 的本地文件
`anchors/extract/.dashscope_key`。**绝不硬编码进库**（本分支可能推远端，硬编码即不可逆泄漏）。

用法：
  PowerShell:  $env:DASHSCOPE_API_KEY="sk-..."; python anchors/extract/run_glm_arm.py -v 06
  或把 key 写进 anchors/extract/.dashscope_key（已 gitignore）后直接：python anchors/extract/run_glm_arm.py -v 06
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "glm-5.2"


def read_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if key:
        return key
    keyfile = ROOT / "anchors" / "extract" / ".dashscope_key"
    if keyfile.exists():
        return keyfile.read_text(encoding="utf-8").strip()
    return ""


def vol2(volume: str) -> str:
    raw = volume.strip().lstrip("卷")
    if raw.endswith(".json"):
        raw = raw[:-5]
    return f"{int(raw):02d}"


def build_arm_prompt(vol: str) -> str:
    """调 build_prompt.py 取该卷 glm 臂的标准提示词正文。"""
    out = subprocess.run(
        [sys.executable, str(ROOT / "anchors" / "build_prompt.py"), "-v", vol, "--arm", "glm"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )
    if out.returncode != 0:
        raise SystemExit(f"build_prompt 失败：{out.stderr}")
    return out.stdout


def assemble_body(vol: str) -> str:
    """读 canon/maintext/卷NN.json，拼成带 scene 号与行号的全卷正文。"""
    data = json.loads((ROOT / "canon" / "maintext" / f"卷{vol}.json").read_text(encoding="utf-8"))
    parts: list[str] = []
    for sc in data["scenes"]:
        parts.append(f"### scene {sc.get('id')}（{sc.get('chapter','')}）")
        for s in sc.get("sents", []):
            parts.append(f"{s.get('id')}: {s.get('text','')}")
    return "\n".join(parts)


def pick_sample(vol: str) -> tuple[str, str]:
    """取一份**更早卷**的 notebook 架构稿当格式样例：防同卷污染、防后卷剧情倒灌。"""
    n = int(vol)
    nb = ROOT / "anchors" / "notebook"
    for cand in (2, 1):  # 优先卷02，其次卷01；都必须 < 当前卷
        if cand < n:
            f = nb / f"锚_卷{cand:02d}.md"
            if f.exists():
                return f"卷{cand:02d}", f.read_text(encoding="utf-8")
    return "", ""  # 卷01/02 自身无更早样例，省略


TRANSPORT_NOTE = """【运行说明 · 必读】你这次通过 API 直调运行，**没有工具、不能执行脚本、不能读写文件**。
- 你在「第一步」要读的 `anchors/README.md` 与一则格式样例，已分别附在下方 <参考·README> 与 <参考·格式样例（另一卷，仅供找手感）> 块里。
- 你在「第二步」本该用 canon_slice 通读的**卷{vol}全卷正文**，已带 scene 号与行号附在最末 <正典正文·卷{vol}> 块里——视同你已用切片脚本通读整卷。行号即 scene.sents[].id，回指时直接用。
- 格式样例取自**另一卷（更早卷）**，只为让你看清「事实观察/暂时读法/暂存弱模式」三层与回指写法，**严禁把样例里的剧情或结论搬到本卷**。
- 你**不要**输出任何「我无法读文件/无法运行脚本」之类的话，也不要复述运行说明；直接进入工作。
- 最终请在回复正文里输出**完整的锚点 markdown 文件内容**（从一级标题 `#` 开始，到文件结束），不要用 ``` 代码块包裹整篇，不要在前后加寒暄。我会把你回复的正文**原样保存**为锚点文件。
- 「完成后回报」那三条请写在 markdown **正文最末**，用一个 `---` 分隔的小节即可。

下面是你的正式任务提示词与全部参考材料。
========================================================================
"""


def build_message(vol: str) -> str:
    prompt = build_arm_prompt(vol).rstrip()
    readme = (ROOT / "anchors" / "README.md").read_text(encoding="utf-8").rstrip()
    sample_vol, sample = pick_sample(vol)
    body = assemble_body(vol).rstrip()
    parts = [TRANSPORT_NOTE.format(vol=vol), prompt,
             "\n\n<参考·README>\n" + readme + "\n</参考·README>"]
    if sample:
        parts.append(f"\n\n<参考·格式样例（{sample_vol}，更早卷，仅供找手感，勿搬剧情）>\n"
                     + sample.rstrip() + "\n</参考·格式样例>")
    parts.append(f"\n\n<正典正文·卷{vol}（带 scene 号与行号）>\n" + body
                 + f"\n</正典正文·卷{vol}>")
    return "\n".join(parts)


def stream_call(content: str, key: str) -> tuple[str, str, dict]:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "stream": True,
        "stream_options": {"include_usage": True},
        "max_tokens": 32000,
        "temperature": 0.7,
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    answer: list[str] = []
    reason: list[str] = []
    usage: dict = {}
    finish = None
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "ignore").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            if obj.get("usage"):
                usage = obj["usage"]
            for ch in obj.get("choices", []):
                delta = ch.get("delta", {})
                if delta.get("content"):
                    answer.append(delta["content"]); sys.stderr.write("."); sys.stderr.flush()
                if delta.get("reasoning_content"):
                    reason.append(delta["reasoning_content"]); sys.stderr.write("·"); sys.stderr.flush()
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
    sys.stderr.write("\n")
    usage["finish_reason"] = finish
    return "".join(answer), "".join(reason), usage


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--volume", required=True)
    vol = vol2(ap.parse_args().volume)

    key = read_key()
    if not key:
        sys.stderr.write("[harness] 缺 key：设 DASHSCOPE_API_KEY 环境变量，或写入 anchors/extract/.dashscope_key（见文件头）。\n")
        return 2

    msg = build_message(vol)
    sys.stderr.write(f"[harness] 卷{vol} 提示词+参考+正文 共 {len(msg)} 字符，调用 {MODEL} …\n")
    answer, reasoning, usage = stream_call(msg, key)

    out_dir = ROOT / "anchors" / "extract" / "glm"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / f"锚_卷{vol}_glm5.2臂_RAW.md"
    raw.write_text(answer, encoding="utf-8")
    if reasoning:
        (out_dir / f"锚_卷{vol}_glm5.2臂_思考.txt").write_text(reasoning, encoding="utf-8")
    sys.stderr.write(f"[harness] usage={json.dumps(usage, ensure_ascii=False)}\n")
    sys.stderr.write(f"[harness] 锚点正文 {len(answer)} 字符 -> {raw}\n")
    # 正文前 40 行便于挑文件名 / workflow agent 回报
    print(f"OUTPUT_PATH={raw}")
    print("\n".join(answer.splitlines()[:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
