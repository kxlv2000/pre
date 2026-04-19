#!/usr/bin/env python3
"""将 index.html 中项目详情页重排为：纵向(3-6) → 横向(7-10) → 历史(11-13)，并更新 data-index。"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "index.html"
text = path.read_text(encoding="utf-8")

# 从「硕士毕设」到「Innovus」结束（不含总结页）
start = "<!-- Slide 7: 硕士毕设 -->"
end_marker = "<!-- Slide 14: Closing -->"
i0 = text.find(start)
i1 = text.find(end_marker)
if i0 < 0 or i1 < 0 or i1 <= i0:
    raise SystemExit("block not found")

block = text[i0:i1]
tail = text[i1:]  # 保留总结页及之后全部内容


def grab(start_comment: str, next_comment: str | None) -> str:
    if next_comment:
        p = re.compile(
            rf"(<!-- {re.escape(start_comment)} -->.*?)(?=<!-- {re.escape(next_comment)} -->)",
            re.DOTALL,
        )
    else:
        p = re.compile(rf"(<!-- {re.escape(start_comment)} -->.*)\Z", re.DOTALL)
    mm = p.search(block)
    if not mm:
        raise SystemExit(f"missing {start_comment}")
    return mm.group(1)


s_master = grab("Slide 7: 硕士毕设", "Slide 8: 校企世界模型")
s_uec = grab("Slide 8: 校企世界模型", "Slide 9: Legacy CV")
s_legacy = grab("Slide 9: Legacy CV", "Slide 10: 内部 Agent（带队实习生）")
s_agent = grab("Slide 10: 内部 Agent（带队实习生）", "Slide 11: Doc compare")
s_doc = grab("Slide 11: Doc compare", "Slide 12: Hackathon")
s_hack = grab("Slide 12: Hackathon", "Slide 13: Innovus")
s_inno = grab("Slide 13: Innovus", None)


def set_index_and_comment(chunk: str, new_num: int, comment: str) -> str:
    chunk = re.sub(r"<!-- Slide \d+:([^>]+) -->", f"<!-- Slide {new_num}:{comment} -->", chunk, count=1)
    chunk = re.sub(r'data-index="\d+"', f'data-index="{new_num}"', chunk, count=1)
    return chunk


ordered = []
ordered.append(set_index_and_comment(s_agent, 7, " 横向 · 内部 Agent"))
ordered.append(set_index_and_comment(s_doc, 8, " 横向 · 文档"))
ordered.append(set_index_and_comment(s_hack, 9, " 横向 · Hackathon"))
ordered.append(set_index_and_comment(s_inno, 10, " 横向 · Innovus"))
ordered.append(set_index_and_comment(s_master, 11, " 历史 · 硕士毕设"))
ordered.append(set_index_and_comment(s_uec, 12, " 历史 · 校企世界模型"))
ordered.append(set_index_and_comment(s_legacy, 13, " 历史 · Legacy BEV"))

new_block = "".join(ordered)
new_text = text[:i0] + new_block + tail
path.write_text(new_text, encoding="utf-8")
print("ok: wrote reordered slides 7-13")
