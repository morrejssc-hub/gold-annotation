#!/usr/bin/env python3
"""units_merge.py —— 把双模型 units 产物按"一致取共识、分歧按人工 audit 裁决"合并成一份 gold。
无 AI：纯机械合并 + 回写人工决定。

输入:
  A = units/<modelA>/<篇>.json（默认 claude）
  B = units/<modelB>/<篇>.json（默认 gpt）
  audit = units/audit_<篇>_v2.tsv（含 audit 列：A / B / 角色名[与角色名…]）
合并规则（逐 uid，按 A 的句序）:
  - (char,role) 集合一致 → 取共识；conf 取两家较低档（保守，利于 target 侧 low-conf 过滤）。
  - 不一致 → 必须在 audit 出现，按 audit 列裁决：
      'A'       → 取 A 的 involves
      'B'       → 取 B 的 involves
      角色名串  → 共识部分(A∩B) + 每个点名角色记为 做/high（人工确认）
  - 不一致却缺 audit → 警告，退回 A∩B 交集（标记 unresolved）。
产物: units/gold/<篇>.json（model="gold"，每条分歧句带 "resolved" 溯源）。

用法: python3 units_merge.py 旅途余白
      python3 units_merge.py 旅途余白 --a units/claude/旅途余白.json --b units/gpt/旅途余白.json
"""
import json, os, csv, re, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
CONF_RANK = {"low": 0, "med": 1, "high": 2}


def load_units(p):
    d = json.load(open(p, encoding="utf-8"))
    by = {u["uid"]: u for u in d["units"]}
    return d, by


def keyset(u):
    return set((x["char"], x["role"]) for x in u["involves"])


def lower_conf(a, b):
    return a if CONF_RANK.get(a, 2) <= CONF_RANK.get(b, 2) else b


def merge_agreed(ua, ub):
    """(char,role) 一致；conf 取两家较低档。"""
    cb = {(x["char"], x["role"]): x.get("conf", "high") for x in ub["involves"]}
    out = []
    for x in ua["involves"]:
        k = (x["char"], x["role"])
        out.append({"char": x["char"], "role": x["role"],
                    "conf": lower_conf(x.get("conf", "high"), cb.get(k, x.get("conf", "high")))})
    return out


def parse_names(s):
    return [n for n in re.split(r"[、,，/\+与和&\s]+", s.strip()) if n]


def parse_involves(s):
    """fix.tsv 的 involves 列：'char:role:conf' 用 ; 或 , 分隔；空串 = [] (叙述)。"""
    s = (s or "").strip()
    if not s:
        return []
    out = []
    for tok in re.split(r"[;；,，]", s):
        tok = tok.strip()
        if not tok:
            continue
        p = tok.split(":")
        out.append({"char": p[0], "role": p[1] if len(p) > 1 else "做",
                    "conf": p[2] if len(p) > 2 else "high"})
    return out


def load_fix(path):
    """共谋盲区人工修正通道：audit 管『两模型分歧』，fix 管『两模型共错』（diff 抓不到，靠抽检发现）。"""
    fix = {}
    if not os.path.exists(path):
        return fix
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            fix[r["uid"]] = (parse_involves(r.get("involves", "")), (r.get("note") or "").strip())
    return fix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--a", default=None)
    ap.add_argument("--b", default=None)
    ap.add_argument("--audit", default=None)
    ap.add_argument("--fix", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    src = args.source
    a_path = args.a or os.path.join(HERE, "units", "claude", src + ".json")
    b_path = args.b or os.path.join(HERE, "units", "gpt", src + ".json")
    audit_path = args.audit or os.path.join(HERE, "units", f"audit_{src}_v2.tsv")
    fix_path = args.fix or os.path.join(HERE, "units", f"fix_{src}.tsv")
    out_path = args.out or os.path.join(HERE, "units", "gold", src + ".json")

    dA, A = load_units(a_path)
    dB, B = load_units(b_path)
    audit = {}
    with open(audit_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            v = (r.get("audit") or "").strip()
            if v:
                audit[r["uid"]] = v

    units, n_agree, n_audit, n_unresolved = [], 0, 0, 0
    stat = {"A": 0, "B": 0, "name": 0}
    for uid in [u["uid"] for u in dA["units"]]:
        ua, ub = A[uid], B[uid]
        if keyset(ua) == keyset(ub):
            units.append({"uid": uid, "text": ua["text"], "involves": merge_agreed(ua, ub)})
            n_agree += 1
            continue
        # 分歧 → 查 audit
        dec = audit.get(uid)
        if dec is None:
            n_unresolved += 1
            common = keyset(ua) & keyset(ub)
            inv = [{"char": c, "role": r, "conf": "low"} for c, r in sorted(common)]
            units.append({"uid": uid, "text": ua["text"], "involves": inv,
                          "resolved": "UNRESOLVED(缺audit→取交集)"})
            print(f"  ⚠ 分歧无 audit: {uid}  {ua['text'][:30]}")
            continue
        n_audit += 1
        if dec == "A":
            inv = [{"char": x["char"], "role": x["role"], "conf": x.get("conf", "high")} for x in ua["involves"]]
            stat["A"] += 1
        elif dec == "B":
            inv = [{"char": x["char"], "role": x["role"], "conf": x.get("conf", "high")} for x in ub["involves"]]
            stat["B"] += 1
        else:
            common = keyset(ua) & keyset(ub)
            conf_a = {(x["char"], x["role"]): x.get("conf", "high") for x in ua["involves"]}
            inv = [{"char": c, "role": r, "conf": conf_a.get((c, r), "high")} for c, r in sorted(common)]
            have = {c for c, _ in common}
            for nm in parse_names(dec):
                if nm not in have:
                    inv.append({"char": nm, "role": "做", "conf": "high"})
            stat["name"] += 1
        units.append({"uid": uid, "text": ua["text"], "involves": inv, "resolved": f"audit:{dec}"})

    # 共谋盲区人工修正（两模型共错，diff/audit 抓不到，靠抽检发现 → fix 通道兜底）
    fix = load_fix(fix_path)
    n_fix = 0
    for u in units:
        if u["uid"] in fix:
            inv, note = fix[u["uid"]]
            u["involves"] = inv
            u["resolved"] = f"fix(共谋盲区):{note}"
            n_fix += 1
            print(f"  ✎ fix {u['uid']}: {note}")

    out = {
        "schema_version": dA.get("schema_version", "units/0.2"),
        "source": src,
        "focalizer": dA.get("focalizer"),
        "cast_ref": dA.get("cast_ref", f"casts/{src}.json"),
        "model": "gold",
        "provenance": {"a": os.path.relpath(a_path, HERE), "b": os.path.relpath(b_path, HERE),
                       "audit": os.path.relpath(audit_path, HERE),
                       "fix": os.path.relpath(fix_path, HERE) if fix else None,
                       "rule": "一致取共识(conf 取低档)；分歧按 audit 裁决；共谋盲区按 fix 覆盖"},
        "units": units,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"合并 {len(units)} 句：一致 {n_agree} | audit 裁决 {n_audit}"
          f"（A={stat['A']} B={stat['B']} 点名={stat['name']}）| fix 共谋盲区 {n_fix} | 未解 {n_unresolved}")
    print(f"gold → {os.path.relpath(out_path, HERE)}")


if __name__ == "__main__":
    main()
