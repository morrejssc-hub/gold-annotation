#!/usr/bin/env python3
"""Extract compact plain-text slices from canon/maintext JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANON_DIR = ROOT / "canon" / "maintext"


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def parse_volume(value: str) -> str:
    raw = value.strip()
    if raw.endswith(".json"):
        raw = raw[:-5]
    if raw.startswith("卷"):
        suffix = raw[1:]
        if suffix.isdigit():
            return f"卷{int(suffix):02d}"
        return raw
    if raw.isdigit():
        return f"卷{int(raw):02d}"
    raise argparse.ArgumentTypeError("卷号须为数字、卷NN 或卷NN.json")


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return number


def non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("不能小于 0")
    return number


def load_volume(canon_dir: Path, volume: str) -> dict[str, Any]:
    path = canon_dir / f"{volume}.json"
    if not path.exists():
        raise SystemExit(f"找不到正文文件：{path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
        raise SystemExit(f"正文结构异常：{path}")
    return data


def find_scene(data: dict[str, Any], scene_id: int) -> dict[str, Any]:
    for scene in data["scenes"]:
        if scene.get("id") == scene_id:
            return scene
    raise SystemExit(f"找不到 scene：{scene_id}")


def list_scenes(data: dict[str, Any]) -> None:
    title = data.get("title", "")
    print(f"{title} scenes")
    for scene in data["scenes"]:
        scene_id = scene.get("id", "?")
        chapter = scene.get("chapter") or ""
        length = scene.get("len")
        if length is None:
            length = len(scene.get("sents", []))
        print(f"{scene_id}\tlen={length}\t{chapter}")


def extract_lines(
    scene: dict[str, Any],
    start: int,
    lines: int | None,
    *,
    number: bool,
    join: bool,
) -> list[str]:
    sents = scene.get("sents")
    if not isinstance(sents, list):
        raise SystemExit("scene 结构异常：缺少 sents[]")

    end = len(sents) if lines is None else min(start + lines, len(sents))
    if start >= len(sents):
        raise SystemExit(f"起始行超出 scene 长度：start={start}, len={len(sents)}")

    selected = sents[start:end]
    if join:
        text = "".join(str(sent.get("text", "")) for sent in selected)
        return [text] if text else []

    output = []
    for sent in selected:
        text = str(sent.get("text", ""))
        if number:
            output.append(f"{sent.get('id', '?')}: {text}")
        else:
            output.append(text)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "从 canon/maintext JSON 按卷、scene 和 scene 内行号输出纯正文。"
            "行号对应 scene.sents[].id，当前快照中从 0 开始。"
        )
    )
    parser.add_argument(
        "-v",
        "--volume",
        type=parse_volume,
        required=True,
        help="卷号，例如 1、01、卷01 或 卷01.json",
    )
    parser.add_argument(
        "-s",
        "--scene",
        type=non_negative_int,
        help="scene id。配合 --list-scenes 可先查看每卷 scene。",
    )
    parser.add_argument(
        "-b",
        "--start",
        type=non_negative_int,
        default=0,
        help="scene 内起始行号，默认 0",
    )
    parser.add_argument(
        "-n",
        "--lines",
        type=positive_int,
        help="读取行数；不填则读取 start 之后的整个 scene",
    )
    parser.add_argument(
        "--number",
        action="store_true",
        help="输出 scene 内行号，便于定位；默认只输出正文",
    )
    parser.add_argument(
        "--join",
        action="store_true",
        help="把选中句子合并为单段输出，进一步压缩换行开销",
    )
    parser.add_argument(
        "--list-scenes",
        action="store_true",
        help="列出指定卷的 scene id、长度和章节名",
    )
    parser.add_argument(
        "--canon-dir",
        type=Path,
        default=DEFAULT_CANON_DIR,
        help=f"正文目录，默认 {DEFAULT_CANON_DIR}",
    )
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    data = load_volume(args.canon_dir, args.volume)

    if args.list_scenes:
        list_scenes(data)
        return 0

    if args.scene is None:
        raise SystemExit("读取正文时必须提供 --scene；或使用 --list-scenes 查看 scene。")

    scene = find_scene(data, args.scene)
    for line in extract_lines(
        scene,
        args.start,
        args.lines,
        number=args.number,
        join=args.join,
    ):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
