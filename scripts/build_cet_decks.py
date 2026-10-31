#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 data/cet4.tsv、data/cet6.tsv 里的词条转换成内置题库 JS（src/bundled-decks.js）。

TSV 每行 4 列：单词 <TAB> 音标 <TAB> 词性. 释义 <TAB> 搭配/例句
生成的卡片：题面＝单词，答案＝音标 + 词性释义 + 搭配；按首字母分组，方便「分类速记」。

用法：
  python scripts/build_cet_decks.py            # 生成 src/bundled-decks.js
  python scripts/build_cet_decks.py --check     # 只校验数据
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "src" / "bundled-decks.js"
BUNDLE_VERSION = "2026-10-31.1"

DECKS = [
    ("cet4.tsv", "四级核心词汇（CET-4）"),
    ("cet6.tsv", "六级核心词汇（CET-6）"),
]


def parse(path: pathlib.Path):
    rows = []
    with path.open(encoding="utf-8-sig") as fh:
        for no, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 4:
                raise SystemExit("%s:%d 期望 4 列，实际 %d 列：%r" % (path.name, no, len(parts), line[:60]))
            word, ipa, meaning, example = (p.replace("\ufeff", "").strip() for p in parts)
            if not word or not meaning:
                raise SystemExit("%s:%d 单词或释义为空" % (path.name, no))
            rows.append({"word": word, "ipa": ipa, "meaning": meaning, "example": example})
    return rows


def build_cards(rows):
    cards = []
    for r in rows:
        head = r["meaning"]
        pos, sep, rest = head.partition(" ")
        answer = r["ipa"]
        if answer:
            answer += "\n\n"
        answer += "**%s** %s" % (pos, rest if sep else "")
        if r["example"]:
            answer += "\n\n" + r["example"]
        letter = r["word"][0].upper()
        cards.append({
            "title": r["word"],
            "question": r["word"],
            "answer": answer.strip(),
            "path": [letter],
        })
    return cards


def generate():
    """从 data/*.tsv 生成 src/bundled-decks.js，返回 {词表: 词数}。"""
    seen = {}
    decks = []
    for fname, label in DECKS:
        path = DATA / fname
        if not path.exists():
            raise SystemExit("缺少词表：%s" % path)
        rows = parse(path)
        for r in rows:
            key = r["word"].lower()
            if key in seen:
                raise SystemExit("重复词：%s（%s 与 %s）" % (r["word"], seen[key], fname))
            seen[key] = fname
        cards = build_cards(rows)
        decks.append({"name": "%s · %d 词" % (label, len(cards)), "cards": cards})
    # 一张卡一行，方便 diff 和人工核对
    lines = ["{"]
    lines.append(' "version": %s,' % json.dumps(BUNDLE_VERSION, ensure_ascii=False))
    lines.append(' "decks": [')
    for di, deck in enumerate(decks):
        lines.append("  {")
        lines.append('   "name": %s,' % json.dumps(deck["name"], ensure_ascii=False))
        lines.append('   "cards": [')
        total = len(deck["cards"])
        for ci, card in enumerate(deck["cards"]):
            lines.append("    " + json.dumps(card, ensure_ascii=False, separators=(",", ":")) + ("," if ci < total - 1 else ""))
        lines.append("   ]")
        lines.append("  }" + ("," if di < len(decks) - 1 else ""))
    lines.append(" ]")
    lines.append("}")
    js = (
        "/* 由 scripts/build_cet_decks.py 从 data/cet*.tsv 生成，勿手改。 */\n"
        "window.MDReviewBundledDecks = " + "\n".join(lines) + ";\n"
    )
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(js)
    return {d["name"]: len(d["cards"]) for d in decks}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验数据，不写文件")
    args = ap.parse_args()

    if args.check:
        total = 0
        for fname, _label in DECKS:
            n = len(parse(DATA / fname))
            print("%s → %d 词" % (fname, n))
            total += n
        print("校验通过，共 %d 词" % total)
        return

    counts = generate()
    for name, n in counts.items():
        print("%s → %d 词" % (name, n))
    print("已写入 %s（%.1f KB）" % (OUT.relative_to(ROOT), OUT.stat().st_size / 1024))


if __name__ == "__main__":
    main()
