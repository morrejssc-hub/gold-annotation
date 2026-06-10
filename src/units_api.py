#!/usr/bin/env python3
"""
units_api.py —— 单轮调用 API 逐篇抽 units（不走 agent），支持自动分段 + 并发。

把 SUBAGENT 规则 + cast + render 全文塞进单条 message，直接吐整章 units JSON。
契合 CLAUDE.md 铁律「不用 agent、整章塞 context、输出 uid 键 JSON」。

分段（治大章单次输出撞 max_tokens）：章句数 > --chunk-sents 时，按 uid 顺序切成多段；
  **每段都把【全文】完整给做上下文（保证归属），只要求模型输出本段的 uid**，最后拼回整章。
并发：--workers N 同时跑 N 篇（线程池，IO 密集有效）。

两个后端：
  --backend openai     OpenAI 兼容（百炼 DashScope / OpenAI）。key: DASHSCOPE_API_KEY / OPENAI_API_KEY
  --backend anthropic  Anthropic /v1/messages。key: ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY

实测：qwen3.7-max + --no-thinking 说话人与 opus 仅差 1 句、206s/小章；deepseek-v4-pro 说话人差 12 句已淘汰。

用法：
  export DASHSCOPE_API_KEY=sk-xxx
  python3 units_api.py 黑狼的摇篮 --model qwen3.7-max --no-thinking --outdir units/qwen
  python3 units_api.py --remaining --scope fanwai --workers 5 --model qwen3.7-max --no-thinking --outdir units/qwen
  python3 units_api.py --remaining --scope fanwai --dry
"""
import os, sys, re, json, glob, time, argparse, threading, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root: 脚本在 src/, 数据在根
MODEL_DEFAULT = "qwen3.7-max"
DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_print_lock = threading.Lock()

RULES = """== 抽取规则(按句、多标签、可重复) ==
- 给【要求提取的每一句】产出一条 unit：{uid, text(逐字原文), involves:[{char, role, conf}]}。
- role 只有两种：
    说 = 引号内的成句口头台词(说话人)。
    做 = 该角色一切非台词表现：动作 / 神态 / 体态 / 显式内心思绪(明确以角色为主语的思考)
         / 拟声·呜咽·吼叫·咬牙·呵欠等非成句发声。
  (不设"想"：思考与动作同归"做"。拟声/发声也归"做"。)
- 显式施事测试(关键，专治环境烘托过标)：一句只在它显式描写某角色在 说/做(该角色为该子句主语/施事)
  时才进 involves。纯写景/氛围/泛论/叙述者议论——即便隐含焦点者心境——一律 involves:[]，不强归焦点者。
  · 心理活动也走显式施事测试：内心活动仅在有显式心理动词(想/觉得/心想/纳闷/猜/感到/想起/不知道/希望/怀疑…)、
    且该角色本人为施事主语时，才算其"做"(conf 降一档 med/low)。无心理动词的裸命题/泛论/比喻/背景概述
    (即便出自第一人称叙述者之口)→ involves:[]，不强归。揣测他人心理(他人为动词主语)→ 至多他人 做:low 或 []。
  · 现场性闸(治非现场动作过标)："做"只给该角色在本场景当下正在做出的动作。
    判据看动作动词本身是否落在非现场算子辖域内——假设(如果/若是/换作)、习惯频率(总是/向来/经常)、
    回忆闪回(当年/那时/曾经…作往事重述)、未遂意图(打算/正要…却没)、泛述概要(这一路/这些天…一笔带过)。
    - 算子只修饰背景名词/旁支从句、动作词仍在主事件线 → 照常现场"做"。
    - 动作词在算子辖域内 → 默认 involves:[](纯非现场叙述)或 做:low(现场被概要压缩、拿不准)，绝不 high。
    - 混合句(现场动作+非现场议论同句) → "做"只挂现场动作那部分，非现场议论不另标。
    - "现场"相对所述场景：闪回被渲染成独立 scene 时，其内部动作照标现场"做"。
- 一句涉及多角色 → involves 列多个(整句重复进各角色，不切分句)。
- char = cast 的 canonical(视角相对称谓归一到所指实体；按场景消解；严格用 cast 里的 canonical 串，群戏无名 → "-")。
- 台词句必恰一个 role=说。但"有引号 ≠ 一定是说"：招牌名/书名/比喻/被引述词/标题等非口头发言的引号，
  按写景或"做"处理，不强标说；无引号的自由间接引语若确为口说，可标说。
  ★同句多引号警觉：一句里既有引号又带"…说/道："标签(引出下句台词)时，本句的引号内容(常是发声/拟声)
   与下句台词分属不同人，别把下句说话人错挂到本句。
- conf ∈ {high, med, low}，锚弱标 low 或弃标。
- 护栏：单元只记 who + 说/做 + 原文。绝不写动作类型/动机/对谁/因果/情绪标签。
- cast 里 playable:false / present:false 的群体/路人/未登场者仍要照常标(它们也在场说做)，只是下游不为其组装样本。
- text 字段务必逐字照搬 render [全文] 原文(含全角引号 “ ” 「 」 等标点)，不可改写成半角，否则破坏 JSON。"""


def build_prompt(source, cast_json, render_txt, focalizer, only_uids=None):
    if only_uids:
        scope_note = (f"\n\n⚠⚠ 分段提取：本章较长，分多次提取。你**必须通读上面【全文】**做归属判断，"
                      f"但【本次只输出】下列 {len(only_uids)} 个 uid 的 units，严格按此顺序、一个不漏、不在列表中的 uid 一律不要输出：\n"
                      + " ".join(only_uids))
        cover = f"覆盖【本段上列 {len(only_uids)} 个 uid】，顺序与列表一致(纯写景句 involves:[])"
    else:
        scope_note = ""
        cover = "覆盖【全章每一句】，uid 顺序与 render [全文] 一致(纯写景句 involves:[])"
    return f"""你是《狼与香辛料》系列的"角色单元"抽取器。本语料用于"在场景下模仿角色回应"的 SFT，
要把每句话归到"哪个角色 说了 / 做了 什么"。这是 gold 数据，宁可弃标(abstain)也不要硬猜。

篇名：{source}　focalizer：{focalizer}

== 角色表(casts/{source}.json，实体清单 canonical / 视角相对称谓 / ambiguous 消解) ==
{cast_json}

== 全文 + 待标台词 uid(render 产物；scene 头 [在场] 是机械名匹配辅助闭集，以正文为准) ==
读完整章再下结论(倒指代/晚点名要读到后文回填)。
{render_txt}

{RULES}{scope_note}

== 输出 ==
只输出纯 JSON、UTF-8，不要任何解释、不要 markdown 代码围栏。结构：
{{
  "schema_version": "units/0.2",
  "source": "{source}", "focalizer": "{focalizer}", "cast_ref": "casts/{source}.json", "model": "{{MODEL}}",
  "units": [
    {{"uid":"2_44","text":"逐字原文…","involves":[{{"char":"罗伦斯","role":"做","conf":"high"}}]}}
  ]
}}
- units {cover}。
- 每句 role=说 至多 1 个；role 仅 {{说,做}}；char ∈ cast.canonical ∪ "-"。"""


def _post(endpoint, body, headers, timeout=900):
    req = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def call(prompt, model, backend, base_url, key, max_tokens, no_thinking=False):
    """返回 (text, input_tokens, output_tokens, stop_reason)。"""
    if backend == "anthropic":
        ep = base_url.rstrip("/")
        if not ep.endswith("/messages"):
            ep += "/v1/messages"
        resp = _post(ep, {"model": model, "max_tokens": max_tokens, "temperature": 0,
                          "messages": [{"role": "user", "content": prompt}]},
                     {"x-api-key": key, "authorization": f"Bearer {key}",
                      "anthropic-version": "2023-06-01", "content-type": "application/json",
                      "anthropic-beta": "context-1m-2025-08-07"})
        text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
        u = resp.get("usage", {})
        return text, u.get("input_tokens", 0), u.get("output_tokens", 0), resp.get("stop_reason")
    else:  # openai 兼容（百炼 DashScope / OpenAI）
        ep = base_url.rstrip("/")
        if not ep.endswith("/chat/completions"):
            ep += "/chat/completions"
        b = {"model": model, "max_tokens": max_tokens, "temperature": 0,
             "messages": [{"role": "user", "content": prompt}]}
        if no_thinking:
            b["enable_thinking"] = False
        resp = _post(ep, b, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        ch = resp["choices"][0]
        u = resp.get("usage", {})
        return ch["message"]["content"], u.get("prompt_tokens", 0), u.get("completion_tokens", 0), ch.get("finish_reason")


def extract_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        t = t[i:j + 1]
    return t


def parse_units(text, render_map):
    """健壮解析 LLM 输出的 units JSON：整体失败则逐行救，text 用 render 原文回填、
    involves 尽力修复（去多余 ]）。返回 (units, n_repaired)。"""
    raw = extract_json(text)
    try:
        return json.loads(raw).get("units", []), 0
    except json.JSONDecodeError:
        pass
    units, rep = [], 0
    for line in raw.splitlines():
        s = line.strip().rstrip(",")
        if not s.startswith('{"uid"') or not s.endswith("}"):
            continue
        try:
            units.append(json.loads(s)); continue
        except json.JSONDecodeError:
            pass
        m = re.match(r'\{"uid"\s*:\s*"([^"]+)"', s)
        if not m:
            continue
        uid, inv = m.group(1), []
        im = re.search(r'"involves"\s*:\s*(\[.*\])\s*\}?\s*$', s)
        if im:
            for fix in (im.group(1), im.group(1).rstrip("]") + "]", "[]"):
                try:
                    inv = json.loads(fix); break
                except json.JSONDecodeError:
                    inv = []
        units.append({"uid": uid, "text": render_map.get(uid, ""), "involves": inv})
        rep += 1
    return units, rep


def cast_of(source):
    return json.load(open(os.path.join(HERE, "casts", source + ".json"), encoding="utf-8"))


def focalizer_of(cast):
    for c in cast.get("cast", []):
        if c.get("is_focalizer"):
            return c["canonical"]
    return ""


def render_uids_list(source):
    p = os.path.join(HERE, "renders", source + ".txt")
    return [l.split("│")[0].strip() for l in open(p, encoding="utf-8") if "│" in l]


def render_map_of(source):
    """有序 dict：uid -> render 全文原文（verbatim 真源，修复坏行时回填 text）。"""
    p = os.path.join(HERE, "renders", source + ".txt")
    m = {}
    for l in open(p, encoding="utf-8"):
        if "│" in l:
            uid, t = l.split("│", 1)
            m[uid.strip()] = t.rstrip("\n")
    return m


def remaining_sources(outdir, scope):
    have = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(outdir, "*.json"))}
    pats = []
    if scope in ("fanwai", "all"):
        pats.append("jsons/*.json")
    if scope in ("vols", "all"):
        pats.append("maintext/*.json")
    out = []
    for pat in pats:
        for p in sorted(glob.glob(os.path.join(HERE, pat))):
            s = os.path.splitext(os.path.basename(p))[0]
            if s in ("幕间",) or s in have:
                continue
            if not os.path.exists(os.path.join(HERE, "renders", s + ".txt")):
                continue
            if not os.path.exists(os.path.join(HERE, "casts", s + ".json")):
                continue
            out.append(s)
    return out


def process_one(s, args, base_url, key):
    """跑一篇（含分段），落盘，返回 (source, msg, in_tok, out_tok)。"""
    outp = os.path.join(args.outdir, s + ".json")
    if os.path.exists(outp) and not args.force:
        return s, "跳过(已存在)", 0, 0
    rp = os.path.join(HERE, "renders", s + ".txt")
    if not os.path.exists(rp):
        return s, "✗ 缺 render", 0, 0
    cast = cast_of(s)
    foc = focalizer_of(cast)
    cast_json = json.dumps(cast, ensure_ascii=False, indent=1)
    render_txt = open(rp, encoding="utf-8").read()
    render_map = render_map_of(s)
    all_uids = list(render_map)
    n = len(all_uids)
    cs = args.chunk_sents
    chunks = [all_uids] if n <= cs else [all_uids[i:i + cs] for i in range(0, n, cs)]
    merged, ti, to, stops, nrep = {}, 0, 0, [], 0
    t0 = time.time()
    for cu in chunks:
        only = cu  # 总是给 uid 清单（单段也给）——逼模型逐句对应，否则单段会跳采样偷懒
        prompt = build_prompt(s, cast_json, render_txt, foc, only)
        try:
            text, a, b, stop = call(prompt, args.model, args.backend, base_url, key, args.max_tokens, args.no_thinking)
        except urllib.error.HTTPError as e:
            return s, f"✗ HTTP {e.code}: {e.read().decode('utf-8','replace')[:160]}", ti, to
        except Exception as e:
            return s, f"✗ {type(e).__name__}: {str(e)[:160]}", ti, to
        ti += a; to += b; stops.append(stop)
        seg_units, rep = parse_units(text, render_map)
        nrep += rep
        want = set(cu)
        for u in seg_units:
            if (only is None) or (u.get("uid") in want):
                merged[u["uid"]] = u
    units = [merged[u] for u in all_uids if u in merged]
    obj = {"schema_version": "units/0.2", "source": s, "focalizer": foc,
           "cast_ref": f"casts/{s}.json", "model": args.model, "units": units}
    json.dump(obj, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    dt = time.time() - t0
    miss = n - len(units)
    trunc = "  ⚠截断" if any(x in ("length", "max_tokens") for x in stops) else ""
    cov = f"{len(units)}/{n}" + ("" if miss == 0 else f"  ⚠缺{miss}")
    rp_note = f"  修复{nrep}行" if nrep else ""
    return s, f"✓ {cov}  {len(chunks)}段  in={ti} out={to}  {dt:.0f}s{trunc}{rp_note}", ti, to


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="*")
    ap.add_argument("--backend", choices=["openai", "anthropic"], default="openai")
    ap.add_argument("--outdir", default=os.path.join(HERE, "units", "qwen"))
    ap.add_argument("--scope", choices=["fanwai", "vols", "all"], default="fanwai", help="--remaining 的范围")
    ap.add_argument("--remaining", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model", default=os.environ.get("UNITS_MODEL", MODEL_DEFAULT))
    ap.add_argument("--base-url", default="")
    ap.add_argument("--max-tokens", type=int, default=32000)
    ap.add_argument("--no-thinking", action="store_true")
    ap.add_argument("--chunk-sents", type=int, default=350, help="超此句数则分段")
    ap.add_argument("--workers", type=int, default=1, help="并发篇数")
    args = ap.parse_args()

    srcs = list(args.sources)
    if args.remaining:
        srcs += remaining_sources(args.outdir, args.scope)
    seen, uniq = set(), []
    for s in srcs:
        if s not in seen:
            seen.add(s); uniq.append(s)
    srcs = uniq
    if args.limit:
        srcs = srcs[:args.limit]
    if not srcs:
        print("没有待跑篇。"); return

    if args.dry:
        print(f"待跑 {len(srcs)} 篇（句数 / 预计段数 @chunk={args.chunk_sents}）：")
        tot = 0
        for s in srcs:
            nn = len(render_uids_list(s)) if os.path.exists(os.path.join(HERE, "renders", s + ".txt")) else 0
            tot += nn
            segs = 1 if nn <= args.chunk_sents else -(-nn // args.chunk_sents)
            print(f"  {s}\t{nn} 句\t{segs} 段")
        print(f"合计约 {tot} 句")
        return

    base_url = args.base_url or (DASHSCOPE_BASE if args.backend == "openai" else os.environ.get("ANTHROPIC_BASE_URL", ""))
    if args.backend == "openai":
        key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    else:
        key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not base_url or not key:
        print("✗ 缺 base_url 或 key（检查对应 env）。"); sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)
    print(f"后端={args.backend} 模型={args.model} no_thinking={args.no_thinking} outdir={args.outdir} "
          f"chunk={args.chunk_sents} workers={args.workers}  共 {len(srcs)} 篇\n")
    tot_in = tot_out = done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_one, s, args, base_url, key): s for s in srcs}
        for f in as_completed(futs):
            s, msg, ti, to = f.result()
            tot_in += ti; tot_out += to; done += 1
            with _print_lock:
                print(f"[{done}/{len(srcs)}] {s}: {msg}", flush=True)
    print(f"\n合计 input={tot_in} output={tot_out} tokens")


if __name__ == "__main__":
    main()
