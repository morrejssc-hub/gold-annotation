#!/usr/bin/env python3
"""回指完整性核查（纯脚本、零模型）——锚点验证的第一层硬闸。

对一份锚点 .md 里每个行级回指 `sNN:MM`：
  - ERROR：该 scene / 行在 canon 卷NN.json 里**不存在**（虚构/越界的回指）。
  - WARN ：该回指**同一 .md 行**上带了引文，但引文在所指行(±2 邻行)里找不到 ≥6 字
            的公共子串——疑似错位/错引（如把 sA 的话标成 sB）。WARN 不阻断，列给人/核查 agent。

只查"忠不忠实(回指对不对得上原文)"，**不评"好不好"**，更不把"像不像原文"当目标。
线级 sNN:MM 的错位它逮；纯散文式的 scene 级归属错（"这发生在 scene17"无引文）它逮不到，
那一类留给核查 agent。用法：
  python anchors/extract/check_refs.py <锚点.md> [更多文件...]   # 卷号从文件名 卷NN 自动识别
  python anchors/extract/check_refs.py <锚点.md> -v 06            # 显式指定卷号
退出码：任一文件有 ERROR → 1，否则 0。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANON = ROOT / "canon" / "maintext"

REF_RE = re.compile(r"s(\d{1,2}):(\d{1,3})")
# 仅认「紧邻配对」：引文(≥8字)收尾后，最多隔几个标点/括号就跟着 sNN:MM。
# 这样多 ref 行各引文配各自的 ref，且滤掉短碎片/分析性 gloss，避免假阳性。
PAIR_RE = re.compile(r"[「『“\"]([^「『」』“”\"]{8,}?)[」』”\"][^一-鿿A-Za-z0-9]{0,4}s(\d{1,2}):(\d{1,3})")
MIN_MATCH = 6  # 引文与原文公共子串达到这么长即认为命中


def load_canon(vol: str) -> dict[int, dict[int, str]]:
    data = json.loads((CANON / f"卷{vol}.json").read_text(encoding="utf-8"))
    out: dict[int, dict[int, str]] = {}
    for sc in data["scenes"]:
        out[sc.get("id")] = {s.get("id"): str(s.get("text", "")) for s in sc.get("sents", [])}
    return out


def norm(s: str) -> str:
    return re.sub(r"\s", "", s)


def longest_match(a: str, b: str) -> int:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0
    m = SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return m.size


def detect_vol(path: Path, override: str | None) -> str | None:
    if override:
        return f"{int(override.lstrip('卷')):02d}"
    m = re.search(r"卷(\d{2})", path.name)
    return m.group(1) if m else None


def check_file(path: Path, vol: str) -> tuple[int, int, int, list[str]]:
    canon = load_canon(vol)
    lines = path.read_text(encoding="utf-8").splitlines()
    total = errors = warns = 0
    msgs: list[str] = []
    for lineno, line in enumerate(lines, 1):
        # ① 存在性：每个 sNN:MM 都查（绝对可靠的硬闸）
        for sc_s, snt_s in REF_RE.findall(line):
            total += 1
            sc, snt = int(sc_s), int(snt_s)
            if sc not in canon:
                errors += 1
                msgs.append(f"  [ERROR] L{lineno} s{sc}:{snt} → scene {sc} 不存在")
            elif snt not in canon[sc]:
                errors += 1
                last = max(canon[sc]) if canon[sc] else "?"
                msgs.append(f"  [ERROR] L{lineno} s{sc}:{snt} → scene {sc} 无行 {snt}（最大 {last}）")
        # ② 引文核查：只认「引文(≥8)」紧邻 sNN:MM 的配对
        for q, sc_s, snt_s in PAIR_RE.findall(line):
            sc, snt = int(sc_s), int(snt_s)
            if sc not in canon or snt not in canon[sc]:
                continue  # 存在性已在①报过
            window = " ".join(canon[sc].get(i, "") for i in range(snt - 2, snt + 3))
            if longest_match(q, window) < MIN_MATCH:
                warns += 1
                qshow = q[:18] + ("…" if len(q) > 18 else "")
                actual = canon[sc][snt][:24]
                msgs.append(f"  [WARN ] L{lineno} s{sc}:{snt} 紧邻引文「{qshow}」在该行±2 找不到≥{MIN_MATCH}字匹配；该行实为「{actual}…」")
    return total, errors, warns, msgs


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-v", "--volume", default=None)
    args = ap.parse_args()

    any_error = False
    for f in args.files:
        path = Path(f)
        vol = detect_vol(path, args.volume)
        if not vol:
            print(f"✗ {path.name}：无法识别卷号（文件名无 卷NN，且未给 -v）")
            any_error = True
            continue
        if not path.is_file():
            print(f"✗ {f}：文件不存在或不可读")
            any_error = True
            continue
        try:
            total, errors, warns, msgs = check_file(path, vol)
        except Exception as e:  # 坏文件不应让整批崩
            print(f"✗ {path.name}：核查出错 {type(e).__name__}: {e}")
            any_error = True
            continue
        flag = "✗" if errors else ("△" if warns else "✓")
        print(f"{flag} {path.name}（卷{vol}）：回指 {total} 处，ERROR {errors}，WARN {warns}")
        for m in msgs:
            print(m)
        any_error = any_error or errors > 0
    return 1 if any_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
