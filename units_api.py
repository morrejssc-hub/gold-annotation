#!/usr/bin/env python3
"""
units_api.py —— 方案 B：单轮调用 Anthropic 兼容 API（含 anyrouter 中转）逐篇抽 units。

不走 agent：把 SUBAGENT 规则 + cast + render 全文塞进单条 message，直接吐整章 units JSON。
契合 CLAUDE.md 铁律「不用 agent、整章塞 context、输出 uid 键 JSON」。
每篇打印 input/output token 用量，便于核 anyrouter 额度成本。

接入（anyrouter 或任意 Anthropic 兼容中转）：
  export ANTHROPIC_BASE_URL=https://anyrouter.top   # 中转根地址（脚本自动补 /v1/messages）
  export ANTHROPIC_AUTH_TOKEN=sk-xxx                # 或 ANTHROPIC_API_KEY
  python3 units_api.py 狼与星空下的远吠 狼与森林色彩      # 指定篇
  python3 units_api.py --remaining --limit 2            # 有 cast 但 units/claude 缺产物的，跑前 2 篇
  python3 units_api.py --remaining --dry               # 只列待跑篇 + 句数估算，不调 API

默认不覆盖已存在产物（--force 覆盖）。输出落 units/claude/<篇>.json。
"""
import os, sys, re, json, glob, time, argparse, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")  # 防 Windows GBK 控制台炸中文
HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "units", "claude")
MODEL_DEFAULT = "claude-opus-4-8"

RULES = """== 抽取规则(按句、多标签、可重复) ==
- 给【全章每一句】产出一条 unit：{uid, text(逐字原文), involves:[{char, role, conf}]}。
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
- char = cast 的 canonical(视角相对称谓归一到所指实体；按场景消解)。群戏无名 → cast 集体实体或 "-"。
- 台词句必恰一个 role=说。但"有引号 ≠ 一定是说"：招牌名/书名/比喻/被引述词/标题等非口头发言的引号，
  按写景或"做"处理，不强标说；无引号的自由间接引语若确为口说，可标说。
  ★同句多引号警觉：一句里既有引号又带"…说/道："标签(引出下句台词)时，本句的引号内容(常是发声/拟声)
   与下句台词分属不同人，别把下句说话人错挂到本句。
- conf ∈ {high, med, low}，锚弱标 low 或弃标。
- 护栏：单元只记 who + 说/做 + 原文。绝不写动作类型/动机/对谁/因果/情绪标签。
- cast 里 playable:false / present:false 的群体/路人/未登场者仍要照常标(它们也在场说做)，只是下游不为其组装样本。"""


def build_prompt(source, cast_json, render_txt, focalizer):
    return f"""你是《狼与香辛料》系列的"角色单元"抽取器。本语料用于"在场景下模仿角色回应"的 SFT，
要把每句话归到"哪个角色 说了 / 做了 什么"。这是 gold 数据，宁可弃标(abstain)也不要硬猜。

篇名：{source}　focalizer：{focalizer}

== 角色表(casts/{source}.json，实体清单 canonical / 视角相对称谓 / ambiguous 消解) ==
{cast_json}

== 全文 + 待标台词 uid(render 产物；scene 头 [在场] 是机械名匹配辅助闭集，以正文为准) ==
读完整章再下结论(倒指代/晚点名要读到后文回填)。
{render_txt}

{RULES}

== 输出 ==
只输出纯 JSON、UTF-8，不要任何解释、不要 markdown 代码围栏。结构：
{{
  "schema_version": "units/0.2",
  "source": "{source}", "focalizer": "{focalizer}", "cast_ref": "casts/{source}.json", "model": "{{MODEL}}",
  "units": [
    {{"uid":"2_44","text":"逐字原文…","involves":[{{"char":"罗伦斯","role":"做","conf":"high"}}]}}
  ]
}}
- units 覆盖【全章每一句】，uid 顺序与 render [全文] 一致(纯写景句 involves:[])。
- 每句 role=说 至多 1 个；role 仅 {{说,做}}；char ∈ cast.canonical ∪ "-"。"""


def call(prompt, model, base_url, key, max_tokens):
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/messages"):
        endpoint += "/v1/messages"
    body = json.dumps({"model": model, "max_tokens": max_tokens, "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(endpoint, data=body, headers={
        "x-api-key": key, "authorization": f"Bearer {key}",
        "anthropic-version": "2023-06-01", "content-type": "application/json",
        "anthropic-beta": "context-1m-2025-08-07"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def extract_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t).strip()  # 剥 markdown fence
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        t = t[i:j + 1]
    return t


def cast_of(source):
    return json.load(open(os.path.join(HERE, "casts", source + ".json"), encoding="utf-8"))


def focalizer_of(cast):
    for c in cast.get("cast", []):
        if c.get("is_focalizer"):
            return c["canonical"]
    return ""


def render_sentcount(source):
    p = os.path.join(HERE, "renders", source + ".txt")
    if not os.path.exists(p):
        return None
    return sum(1 for l in open(p, encoding="utf-8") if "│" in l)


def remaining_sources():
    have = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(OUTDIR, "*.json"))}
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, "casts", "*.json"))):
        s = os.path.splitext(os.path.basename(p))[0]
        if s in have:
            continue
        if not os.path.exists(os.path.join(HERE, "renders", s + ".txt")):
            continue
        out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="*", help="篇名（不带扩展名）")
    ap.add_argument("--remaining", action="store_true", help="有 cast+render 但 units/claude 缺产物的全部")
    ap.add_argument("--limit", type=int, default=0, help="最多跑前 N 篇")
    ap.add_argument("--dry", action="store_true", help="只列待跑篇 + 句数，不调 API")
    ap.add_argument("--force", action="store_true", help="覆盖已存在产物")
    ap.add_argument("--model", default=os.environ.get("UNITS_MODEL", MODEL_DEFAULT))
    ap.add_argument("--base-url", default=os.environ.get("ANTHROPIC_BASE_URL", ""))
    ap.add_argument("--max-tokens", type=int, default=32000)
    args = ap.parse_args()

    srcs = list(args.sources)
    if args.remaining:
        srcs += remaining_sources()
    seen, uniq = set(), []
    for s in srcs:
        if s not in seen:
            seen.add(s); uniq.append(s)
    srcs = uniq
    if args.limit:
        srcs = srcs[:args.limit]

    if not srcs:
        print("没有待跑篇。用法见脚本头注释。"); return

    if args.dry:
        print(f"待跑 {len(srcs)} 篇（句数估算）：")
        tot = 0
        for s in srcs:
            n = render_sentcount(s) or 0
            tot += n
            print(f"  {s}\t{n} 句")
        print(f"合计约 {tot} 句")
        return

    key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not args.base_url:
        print("✗ 缺 ANTHROPIC_BASE_URL（anyrouter 根地址）。export 后再跑。"); sys.exit(1)
    if not key:
        print("✗ 缺 ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY。"); sys.exit(1)

    os.makedirs(OUTDIR, exist_ok=True)
    print(f"模型={args.model}  base={args.base_url}  max_tokens={args.max_tokens}\n")
    tot_in = tot_out = 0
    for s in srcs:
        outp = os.path.join(OUTDIR, s + ".json")
        if os.path.exists(outp) and not args.force:
            print(f"跳过(已存在) {s}"); continue
        rp = os.path.join(HERE, "renders", s + ".txt")
        if not os.path.exists(rp):
            print(f"✗ 缺 render {s}"); continue
        cast = cast_of(s)
        foc = focalizer_of(cast)
        prompt = build_prompt(s, json.dumps(cast, ensure_ascii=False, indent=1),
                              open(rp, encoding="utf-8").read(), foc)
        nsent = render_sentcount(s)
        print(f"▶ {s}　{nsent} 句　发起…", flush=True)
        t0 = time.time()
        try:
            resp = call(prompt, args.model, args.base_url, key, args.max_tokens)
        except urllib.error.HTTPError as e:
            print(f"  ✗ HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}"); continue
        except Exception as e:
            print(f"  ✗ {type(e).__name__}: {str(e)[:200]}"); continue
        dt = time.time() - t0
        usage = resp.get("usage", {})
        ti, to = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        tot_in += ti; tot_out += to
        stop = resp.get("stop_reason")
        text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
        raw = extract_json(text)
        try:
            obj = json.loads(raw)
            obj["model"] = args.model
            json.dump(obj, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            nunits = len(obj.get("units", []))
            warn = "  ⚠ 截断(max_tokens)!" if stop == "max_tokens" else ""
            cover = "" if nunits == nsent else f"  ⚠ 句数 {nunits}≠render {nsent}"
            print(f"  ✓ {nunits} units  in={ti} out={to}  {dt:.0f}s  stop={stop}{warn}{cover}")
            print(f"    → {outp}（跑完用 units_check.py 卡）")
        except json.JSONDecodeError as e:
            badp = outp + ".raw.txt"
            open(badp, "w", encoding="utf-8").write(text)
            print(f"  ✗ JSON 解析失败({e})  in={ti} out={to} stop={stop}  原文存 {badp}")
    print(f"\n本次合计 input={tot_in} output={tot_out} tokens（核对 anyrouter 额度扣减）")


if __name__ == "__main__":
    main()
