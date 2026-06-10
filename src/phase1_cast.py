#!/usr/bin/env python3
"""
phase1_cast.py —— Phase 1: 整章 → 角色表(cast sheet)。

把一篇 json 的全文 + focalizer + 全局专名别名种子, 拼成提示词, 交给 LLM 产出
casts/<source>.json(schema 见 PHASE1.md / casts/后日谈.json)。这一步**每章一次**,
解决: 倒指代回填、视角相对称谓(主人/旅伴…)、泛称按场景消解、跨章点名标★。

非 agent、非逐句。整章能塞进 context, 所以一次调用即可。产物小、可人工秒审。

后端(--backend):
  dump    只把提示词打到 stdout/文件(默认)。无需 key, 可直接贴进 Claude Max。
  bailian 阿里百炼(DashScope, OpenAI 兼容)。 env: DASHSCOPE_API_KEY
  codex   OpenAI 兼容。              env: OPENAI_API_KEY  (--base-url 可改)
  claude  Anthropic。               env: ANTHROPIC_API_KEY

用法:
  python3 phase1_cast.py jsons/后日谈.json --backend dump > prompt.txt
  python3 phase1_cast.py jsons/后日谈.json --backend bailian --model qwen-max
  python3 phase1_cast.py jsons/后日谈.json --backend claude  --model claude-opus-4-8
"""
import sys, os, json, csv, argparse, urllib.request

SCHEMA_HINT = '''输出**纯 JSON**(不要 markdown 代码块), 结构:
{
  "schema_version": "phase1-cast/0.1",
  "source": "<篇名>",
  "focalizer": "<视角角色 canonical>",
  "focalizer_note": "<该视角下'主人'等关系称谓指谁;一句话>",
  "cast": [ {
    "canonical": "<归一后的标准名,优先用专名;无专名才用最稳定的称谓>",
    "aka": ["<所有专名/别名/绰号>"],
    "appellations": ["<关系/职务称谓:主人、祭司大人、旅伴、父亲… 视角相对,不进全局表>"],
    "descriptors": ["<叙述中的描述性/比喻性指代:女子、如狼般的女子、那只羊>"],
    "present": true,                     // 本篇是否登场(可能有台词); 仅被提及=false
    "present_scope": "<可选:如'仅场景1'/'场景3起'>",
    "is_focalizer": false,              // 仅视角角色为 true
    "speech": "<语癖/口吻签名,供后续判说话人;如赫萝:汝/咱/呐>",
    "persona": "<一句话人设:身份/性格/关系>",
    "confidence": "high|medium|low",
    "evidence": {"first_mention":"<sceneid_sentid>", "first_named":"<sceneid_sentid>"},
    "note": "<可选:倒指代等要点>"
  } ],
  "ambiguous": [ {"expression":"<泛称如'女子'>","issue":"...","resolution":"<按场景指谁>","action":"..."} ],
  "needs_registry": [ {"where":"<sceneid_sentid>","expression":"...","issue":"只能靠系列正典推断","action":"标★"} ]
}'''

RULES = '''规则:
1. 读完整章再下结论。**倒指代必须回填**:开头以"女子/来客/那男人"出现、后文才点名的,把名字补到该实体,并在 evidence 标 first_mention 与 first_named。
2. focalizer 视角下的关系称谓(主人/旅伴/父亲/当家的…)放进对应实体的 appellations,**不要**当独立实体。focalizer_note 写明"主人"=谁。
3. 泛称(如"女子")若随场景指不同人,**不要**塞进某个实体的 aka, 放进 ambiguous,写清按场景如何消解。
4. 仅被提及、本篇无台词的角色(如远方的婚礼主角)present=false,仍要登记(便于解析"那两人"等)。
5. 只能靠**系列正典/主篇情节**才能点名的(本章正文从不写出其名),放进 needs_registry 标★,不要硬猜进 cast。
6. canonical 尽量复用给定的"全局专名种子";没有的用本篇最稳定的名字。'''


def load_focalizer(source, path="focalizers.tsv"):
    if not os.path.exists(path):
        return ""
    for r in csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"):
        if r.get("source") == source:
            return (r.get("focalizer") or "").strip()
    return ""


def render_chapter(doc):
    out = []
    if doc.get("abstract"):
        out.append("【内容提要】" + doc["abstract"])
    for sc in doc.get("scenes", []):
        out.append(f"\n##### 场景 {sc['id']} #####")
        for s in sc["sents"]:
            out.append(f"[{sc['id']}_{s['id']}] {s['text']}")
    return "\n".join(out)


def build_prompt(doc, source, focalizer, aliases_path="aliases.json"):
    seed = ""
    if os.path.exists(aliases_path):
        raw = json.load(open(aliases_path, encoding="utf-8"))
        seed = ", ".join(k for k in raw if not k.startswith("_"))
    foc = focalizer or "(未知,请你从全文判断;第一人称'我'往往就是视角角色)"
    return f"""你是小说《狼与香辛料》系列的角色解析器。任务:读完下面**整章**正文,产出该章的【角色表】。

篇名: {source}
视角角色(focalizer): {foc}
全局专名种子(canonical 优先复用): {seed}

{RULES}

{SCHEMA_HINT}

================ 正文开始 ================
{render_chapter(doc)}
================ 正文结束 ================

现在只输出该章角色表的纯 JSON。"""


def call_openai_compatible(prompt, base_url, model, key):
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": model, "temperature": 0,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def call_anthropic(prompt, model, key):
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": model, "max_tokens": 8192, "temperature": 0,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["content"][0]["text"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--backend", choices=["dump", "bailian", "codex", "claude"], default="dump")
    ap.add_argument("--model", default="")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--aliases", default="aliases.json")
    ap.add_argument("--focalizers", default="focalizers.tsv")
    ap.add_argument("--out-dir", default="casts")
    args = ap.parse_args()

    doc = json.load(open(args.json_path, encoding="utf-8"))
    source = doc.get("title") or os.path.splitext(os.path.basename(args.json_path))[0]
    focalizer = load_focalizer(source, args.focalizers)
    prompt = build_prompt(doc, source, focalizer, args.aliases)

    if args.backend == "dump":
        sys.stdout.write(prompt + "\n")
        return

    if args.backend == "bailian":
        base = args.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        key = os.environ.get("DASHSCOPE_API_KEY", "")
        text = call_openai_compatible(prompt, base, args.model or "qwen-max", key)
    elif args.backend == "codex":
        base = args.base_url or "https://api.openai.com/v1"
        key = os.environ.get("OPENAI_API_KEY", "")
        text = call_openai_compatible(prompt, base, args.model or "gpt-4o", key)
    else:  # claude
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        text = call_anthropic(prompt, args.model or "claude-opus-4-8", key)

    text = text.strip()
    if text.startswith("```"):                       # 容错: 去掉 markdown 围栏
        text = text.split("```", 2)[1].lstrip("json").strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        sys.stderr.write("⚠ 模型输出非合法 JSON, 原样落盘待人工修:\n")
        obj = None
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, source + (".json" if obj else ".raw.txt"))
    open(out, "w", encoding="utf-8").write(
        json.dumps(obj, ensure_ascii=False, indent=2) if obj else text)
    sys.stderr.write(f"→ {out}\n")


if __name__ == "__main__":
    main()
