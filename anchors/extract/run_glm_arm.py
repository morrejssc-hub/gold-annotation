#!/usr/bin/env python3
"""一次性 harness：用阿里百炼 glm-5.2 跑「外部真模型臂」（替代 codex 臂）逐卷锚点。

定位：本脚本只做**纯传输**——把 build_prompt.py 的标准单臂提示词 + README（方法）
+ 一份更早卷的格式样例 + 目标卷全卷正文，原样喂给 glm-5.2，再把模型写的锚点原样落盘。
不注入任何读法，保住该臂相对 Claude 臂的独立异质对比。

GLM 经 API 直调，没有工具/文件系统，无法自己跑 canon_slice、无法写文件，
故由本脚本代为切片整卷并内联正文（视同它已通读整卷），它在回复正文里直接吐锚点 markdown。

用法：python anchors/extract/run_glm_arm.py -v 03
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "glm-5.2"
# key 从环境变量读，绝不硬编码进库（这分支可能推远端，硬编码即不可逆泄漏）：
#   PowerShell:  $env:DASHSCOPE_API_KEY = "sk-..."; python anchors/extract/run_glm_arm.py -v 03
API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

TRANSPORT_NOTE = """【运行说明 · 必读】你这次通过 API 直调运行，**没有工具、不能执行脚本、不能读写文件**。
- 你在「第一步」要读的 `anchors/README.md` 与一则格式样例，已分别附在下方 <参考·README> 与 <参考·格式样例（另一卷，仅供找手感）> 块里。
- 你在「第二步」本该用 canon_slice 通读的**卷{vol}全卷正文**，已带 scene 号与行号附在最末 <正典正文·卷{vol}> 块里——视同你已用切片脚本通读整卷。行号即 scene.sents[].id，回指时直接用。
- 格式样例取自**另一卷**，只为让你看清「事实观察/暂时读法/暂存弱模式」三层与回指写法，**严禁把样例里的剧情或结论搬到本卷**。
- 你**不要**输出任何「我无法读文件/无法运行脚本」之类的话，也不要复述运行说明；直接进入工作。
- 最终请在回复正文里输出**完整的锚点 markdown 文件内容**（从一级标题 `#` 开始，到文件结束），不要用 ``` 代码块包裹整篇，不要在前后加寒暄。我会把你回复的正文**原样保存**为锚点文件。
- 「完成后回报」那三条请写在 markdown **正文最末**，用一个 `---` 分隔的小节即可。

下面是你的正式任务提示词与全部参考材料。
========================================================================
"""


def build_message(vol: str) -> str:
    prompt = (ROOT / "canon" / ".glm_v3_prompt.txt").read_text(encoding="utf-8")
    readme = (ROOT / "anchors" / "README.md").read_text(encoding="utf-8")
    sample = (ROOT / "anchors" / "notebook" / "锚_卷02.md").read_text(encoding="utf-8")
    body = (ROOT / "canon" / ".glm_v3_body.txt").read_text(encoding="utf-8")
    parts = [
        TRANSPORT_NOTE.format(vol=vol),
        prompt.rstrip(),
        "\n\n<参考·README>\n" + readme.rstrip() + "\n</参考·README>",
        "\n\n<参考·格式样例（另一卷，仅供找手感，勿搬剧情）>\n" + sample.rstrip()
        + "\n</参考·格式样例>",
        "\n\n<正典正文·卷" + vol + "（带 scene 号与行号）>\n" + body.rstrip()
        + "\n</正典正文·卷" + vol + ">",
    ]
    return "\n".join(parts)


def stream_call(content: str) -> tuple[str, str, dict]:
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
        headers={"Authorization": "Bearer " + API_KEY,
                 "Content-Type": "application/json"},
    )
    answer_chunks: list[str] = []
    reason_chunks: list[str] = []
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
                    answer_chunks.append(delta["content"])
                    sys.stderr.write(".")
                    sys.stderr.flush()
                rc = delta.get("reasoning_content")
                if rc:
                    reason_chunks.append(rc)
                    sys.stderr.write("·")
                    sys.stderr.flush()
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
    sys.stderr.write("\n")
    usage["finish_reason"] = finish
    return "".join(answer_chunks), "".join(reason_chunks), usage


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--volume", default="03")
    args = ap.parse_args()
    vol = args.volume

    if not API_KEY:
        sys.stderr.write("[harness] 缺 DASHSCOPE_API_KEY 环境变量；先设置再跑（见文件头注释）。\n")
        return 2

    msg = build_message(vol)
    sys.stderr.write(f"[harness] 提示词+参考+正文 共 {len(msg)} 字符，调用 {MODEL} …\n")
    answer, reasoning, usage = stream_call(msg)

    out_dir = ROOT / "anchors" / "extract" / "codex"
    raw_path = out_dir / f"锚_卷{vol}_glm5.2臂_RAW.md"
    raw_path.write_text(answer, encoding="utf-8")
    if reasoning:
        (out_dir / f"锚_卷{vol}_glm5.2臂_思考.txt").write_text(reasoning, encoding="utf-8")
    sys.stderr.write(f"[harness] usage={json.dumps(usage, ensure_ascii=False)}\n")
    sys.stderr.write(f"[harness] 锚点正文 {len(answer)} 字符 -> {raw_path}\n")
    sys.stderr.write(f"[harness] 思考 {len(reasoning)} 字符\n")
    # 打印正文前 40 行便于挑文件名
    print("\n".join(answer.splitlines()[:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
