#!/usr/bin/env python3
"""提交/轮询百炼 Batch（需 DASHSCOPE_API_KEY）。

用法：
  python submit_batch.py check                # 验密钥 + 列出含 qwen3.7/deepseek 的模型 ID
  python submit_batch.py submit               # 上传三个 JSONL 并创建 batch，句柄存 batches.json
  python submit_batch.py poll                 # 轮询状态；完成则下载到 batch_output.<model>.jsonl
"""
import json, sys, time, os
from pathlib import Path
from openai import OpenAI

OUT = Path(__file__).resolve().parent
BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODELS = ["qwen3.7-plus", "qwen3.7-max"]  # deepseek-v4-pro 不在 Batch 白名单，走实时（run_realtime.py）

key = os.environ.get("DASHSCOPE_API_KEY", "")
if not key:
    sys.exit("✗ 缺 DASHSCOPE_API_KEY")
client = OpenAI(api_key=key, base_url=BASE)


def check():
    ids = [m.id for m in client.models.list()]
    hits = [i for i in ids if "3.7" in i or "deepseek" in i.lower()]
    print("\n".join(sorted(hits)) or "（无匹配，打印全部前50）\n" + "\n".join(ids[:50]))


def submit():
    handles = {}
    for model in MODELS:
        f = OUT / f"batch_input.{model}.jsonl"
        up = client.files.create(file=f.open("rb"), purpose="batch")
        b = client.batches.create(input_file_id=up.id,
                                  endpoint="/v1/chat/completions",
                                  completion_window="24h")
        handles[model] = {"file_id": up.id, "batch_id": b.id}
        print(f"{model}: batch {b.id} created")
    (OUT / "batches.json").write_text(json.dumps(handles, indent=1), encoding="utf-8")


def poll():
    handles = json.loads((OUT / "batches.json").read_text())
    pending = dict(handles)
    while pending:
        for model, h in list(pending.items()):
            b = client.batches.retrieve(h["batch_id"])
            print(f"{model}: {b.status} ({getattr(b.request_counts, 'completed', '?')}/"
                  f"{getattr(b.request_counts, 'total', '?')})")
            if b.status == "completed":
                content = client.files.content(b.output_file_id).text
                (OUT / f"batch_output.{model}.jsonl").write_text(content, encoding="utf-8")
                if b.error_file_id:
                    (OUT / f"batch_errors.{model}.jsonl").write_text(
                        client.files.content(b.error_file_id).text, encoding="utf-8")
                print(f"  -> batch_output.{model}.jsonl 已下载")
                del pending[model]
            elif b.status in ("failed", "expired", "cancelled"):
                print(f"  ✗ {model} 终态 {b.status}：{b}")
                del pending[model]
        if pending:
            time.sleep(60)


if __name__ == "__main__":
    {"check": check, "submit": submit, "poll": poll}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
