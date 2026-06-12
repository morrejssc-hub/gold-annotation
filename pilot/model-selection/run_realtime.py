#!/usr/bin/env python3
"""deepseek-v4-pro 实时跑批（Batch 白名单不含 v4，偏差记录于 PROTOCOL）。
读 batch_input.deepseek-v4-pro.jsonl，逐条实时调用，输出与 batch 同构的 jsonl。"""
import json, os, sys, time
from pathlib import Path
from openai import OpenAI

OUT = Path(__file__).resolve().parent
MODEL = "deepseek-v4-pro"
client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"],
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

lines = (OUT / f"batch_input.{MODEL}.jsonl").read_text(encoding="utf-8").splitlines()
out_path = OUT / f"batch_output.{MODEL}.jsonl"
done = set()
if out_path.exists():
    done = {json.loads(l)["custom_id"] for l in out_path.read_text(encoding="utf-8").splitlines()}

with out_path.open("a", encoding="utf-8") as f:
    for line in lines:
        req = json.loads(line)
        if req["custom_id"] in done:
            continue
        body = dict(req["body"])
        body.pop("seed", None)  # 实时接口对部分三方模型不支持 seed，统一去掉并记录
        extra = {"enable_thinking": body.pop("enable_thinking", False)}
        for attempt in range(3):
            try:
                r = client.chat.completions.create(**body, extra_body=extra)
                f.write(json.dumps({
                    "custom_id": req["custom_id"],
                    "response": {"body": r.model_dump()},
                }, ensure_ascii=False) + "\n")
                f.flush()
                print(req["custom_id"], "ok")
                break
            except Exception as e:
                print(req["custom_id"], f"retry{attempt}: {e}", file=sys.stderr)
                if attempt == 2:
                    raise
                time.sleep(5)
print("done")
