#!/usr/bin/env python3
"""
units_batch.py —— 用百炼 Batch API（50% 成本、异步）批量抽 units。OpenAI 兼容，urllib 实现。

复用 units_api 的 build_prompt / 分段 / render_map / parse_units(repair)。
每篇按 --chunk-sents 分段，每段一个请求行；custom_id = "<篇名>__seg<i>"；enable_thinking=false（body 顶层）。

流程：
  1) build  —— 生成 JSONL（每段一行请求）
       python3 units_batch.py build --remaining --scope fanwai --outdir units/qwen \
           --model qwen3.7-max --chunk-sents 350 --jsonl tmp/batch_fanwai.jsonl
  2) submit —— 上传 JSONL + 创建 batch，打印 batch_id（并写 <jsonl>.batchid）
       python3 units_batch.py submit --jsonl tmp/batch_fanwai.jsonl
  3) fetch  —— 查询/轮询；完成后下载结果、按篇合并落盘 units/<outdir>/<篇>.json
       python3 units_batch.py fetch --batch-id batch_xxx --outdir units/qwen --model qwen3.7-max [--poll]

需 DASHSCOPE_API_KEY。Batch 下 qwen3.7-max 单请求上下文 256K，成本为实时 50%，仅成功请求计费。
"""
import os, sys, json, time, uuid, argparse, urllib.request, urllib.error
from collections import defaultdict
import units_api as U

sys.stdout.reconfigure(encoding="utf-8")
BASE = U.DASHSCOPE_BASE


def _key():
    k = os.environ.get("DASHSCOPE_API_KEY", "")
    if not k:
        print("✗ 缺 DASHSCOPE_API_KEY"); sys.exit(1)
    return k


def upload_file(key, path):
    boundary = "----unitsbatch" + uuid.uuid4().hex
    with open(path, "rb") as f:
        content = f.read()
    parts = []
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="purpose"\r\n\r\nbatch\r\n'.encode())
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                  f'filename="{os.path.basename(path)}"\r\nContent-Type: application/jsonl\r\n\r\n').encode())
    parts.append(content + b"\r\n")
    parts.append(f'--{boundary}--\r\n'.encode())
    body = b"".join(parts)
    req = urllib.request.Request(BASE + "/files", data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    return json.load(urllib.request.urlopen(req, timeout=300))["id"]


def create_batch(key, file_id, window):
    body = json.dumps({"input_file_id": file_id, "endpoint": "/v1/chat/completions",
                       "completion_window": window}).encode()
    req = urllib.request.Request(BASE + "/batches", data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def get_batch(key, bid):
    req = urllib.request.Request(BASE + f"/batches/{bid}", headers={"Authorization": f"Bearer {key}"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def download(key, fid):
    req = urllib.request.Request(BASE + f"/files/{fid}/content", headers={"Authorization": f"Bearer {key}"})
    return urllib.request.urlopen(req, timeout=300).read().decode("utf-8")


def cmd_build(args):
    srcs = list(args.sources)
    if args.remaining:
        srcs += U.remaining_sources(args.outdir, args.scope)
    seen, uniq = set(), []
    for s in srcs:
        if s not in seen:
            seen.add(s); uniq.append(s)
    srcs = uniq
    if args.limit:
        srcs = srcs[:args.limit]
    lines, perfile = [], 0
    for s in srcs:
        cast = U.cast_of(s); foc = U.focalizer_of(cast)
        cast_json = json.dumps(cast, ensure_ascii=False, indent=1)
        render_txt = open(os.path.join(U.HERE, "renders", s + ".txt"), encoding="utf-8").read()
        uids = U.render_uids_list(s); n = len(uids); cs = args.chunk_sents
        chunks = [uids] if n <= cs else [uids[i:i + cs] for i in range(0, n, cs)]
        for i, cu in enumerate(chunks):
            only = cu  # 总是给 uid 清单（单段也给）——逼模型逐句对应，否则单段会跳采样偷懒
            prompt = U.build_prompt(s, cast_json, render_txt, foc, only)
            req = {"custom_id": f"{s}__seg{i}", "method": "POST", "url": "/v1/chat/completions",
                   "body": {"model": args.model, "enable_thinking": False, "max_tokens": args.max_tokens,
                            "messages": [{"role": "user", "content": prompt}]}}
            lines.append(json.dumps(req, ensure_ascii=False))
        perfile += 1
    os.makedirs(os.path.dirname(args.jsonl) or ".", exist_ok=True)
    open(args.jsonl, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    size = os.path.getsize(args.jsonl) / 1e6
    print(f"生成 {len(lines)} 请求（{perfile} 篇）→ {args.jsonl}  ({size:.1f} MB)")
    if size > 500:
        print("⚠ 文件 >500MB，需拆分多个任务")


def cmd_submit(args):
    key = _key()
    fid = upload_file(key, args.jsonl)
    print("input_file_id:", fid)
    b = create_batch(key, fid, args.window)
    print(f"batch_id: {b['id']}  status: {b['status']}")
    open(args.jsonl + ".batchid", "w").write(b["id"])
    print(f"（已写 {args.jsonl}.batchid；用 fetch --batch-id {b['id']} 取结果）")


def cmd_fetch(args):
    key = _key()
    bid = args.batch_id
    while True:
        b = get_batch(key, bid)
        rc = b.get("request_counts", {})
        print(f"status={b['status']}  counts={rc}", flush=True)
        if b["status"] in ("completed", "failed", "expired", "cancelled"):
            break
        if not args.poll:
            print("未完成，稍后再 fetch（或加 --poll 轮询）"); return
        time.sleep(args.poll_interval)
    if b["status"] != "completed":
        print(f"任务终态 {b['status']}，无结果。");
        if b.get("errors"):
            print("errors:", json.dumps(b["errors"], ensure_ascii=False)[:400])
        return
    out = download(key, b["output_file_id"])
    bysrc = defaultdict(list)
    nfail = 0
    for line in out.splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        cid = o["custom_id"]; src = cid.rsplit("__seg", 1)[0]
        resp = o.get("response")
        if not resp or resp.get("status_code") != 200:
            nfail += 1; print("✗", cid, str(o.get("error"))[:120]); continue
        bysrc[src].append(resp["body"]["choices"][0]["message"]["content"])
    os.makedirs(args.outdir, exist_ok=True)
    for src, contents in sorted(bysrc.items()):
        rmap = U.render_map_of(src); all_uids = list(rmap); merged, nrep = {}, 0
        for c in contents:
            us, rep = U.parse_units(c, rmap); nrep += rep
            for u in us:
                merged[u["uid"]] = u
        units = [merged[u] for u in all_uids if u in merged]
        obj = {"schema_version": "units/0.2", "source": src, "focalizer": U.focalizer_of(U.cast_of(src)),
               "cast_ref": f"casts/{src}.json", "model": args.model, "units": units}
        json.dump(obj, open(os.path.join(args.outdir, src + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        miss = len(all_uids) - len(units)
        print(f"  {src}: {len(units)}/{len(all_uids)}"
              + (f"  ⚠缺{miss}" if miss else "") + (f"  修复{nrep}行" if nrep else ""))
    if b.get("error_file_id"):
        print("⚠ 有 error_file，下载查详情：", b["error_file_id"])
    print(f"落盘完成（失败请求 {nfail}）。逐篇跑 units_check.py 复核。")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.set_defaults(fn=cmd_build)
    b.add_argument("sources", nargs="*")
    b.add_argument("--remaining", action="store_true")
    b.add_argument("--scope", choices=["fanwai", "vols", "all"], default="fanwai")
    b.add_argument("--outdir", default="units/qwen", help="判断已存在产物用，也是 fetch 落盘目录")
    b.add_argument("--limit", type=int, default=0)
    b.add_argument("--model", default="qwen3.7-max")
    b.add_argument("--chunk-sents", type=int, default=350)
    b.add_argument("--max-tokens", type=int, default=32000)
    b.add_argument("--jsonl", default="tmp/batch.jsonl")
    s = sub.add_parser("submit"); s.set_defaults(fn=cmd_submit)
    s.add_argument("--jsonl", default="tmp/batch.jsonl")
    s.add_argument("--window", default="24h")
    f = sub.add_parser("fetch"); f.set_defaults(fn=cmd_fetch)
    f.add_argument("--batch-id", required=True)
    f.add_argument("--outdir", default="units/qwen")
    f.add_argument("--model", default="qwen3.7-max")
    f.add_argument("--poll", action="store_true")
    f.add_argument("--poll-interval", type=int, default=60)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
