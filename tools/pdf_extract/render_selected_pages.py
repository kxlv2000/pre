#!/usr/bin/env python3
"""用 PyMuPDF 将指定 PDF 页栅格化为 interview_assets/selected/ 下的配图（整页，避免 pypdf 抽到色块小图）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "interview_assets" / "selected"
MAT = fitz.Matrix(2.25, 2.25)

# (相对 ROOT 的 PDF 路径, 1-based 页码, 输出文件名)
JOBS: list[tuple[str, int, str]] = [
    ("新素材/Innovus capital 创业/商业提案 v3.13.pdf", 2, "sel_innovus_proposal_exec.png"),
    ("新素材/Innovus capital 创业/SAMPLE Equity Research Report on Verizon.pdf", 4, "sel_equity_research_sample.png"),
    (
        "新素材/Horizontal AI application/获奖项目人才 365，晋升依据/022+人才365+卿博文 0908.pdf",
        9,
        "sel_talent365_slide.png",
    ),
    ("新素材/University-Enterprise-Collaborate project/世界模型技术规划评审.pdf", 4, "sel_uec_trd_slide.png"),
]


def master_pdf() -> Path:
    cands = list((ROOT / "新素材").glob("Master*/stage sharing.pdf"))
    if not cands:
        raise FileNotFoundError("未找到 新素材/Master*/stage sharing.pdf")
    return cands[0]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = list(JOBS)
    jobs.append((str(master_pdf()), 13, "sel_master_sd_compare.png"))
    for rel, page_one_based, name in jobs:
        pdf = ROOT / rel
        if not pdf.exists():
            print(f"[skip] missing {pdf}", file=sys.stderr)
            continue
        doc = fitz.open(pdf)
        i = page_one_based - 1
        if i < 0 or i >= len(doc):
            print(f"[skip] {pdf.name} page {page_one_based} out of range", file=sys.stderr)
            doc.close()
            continue
        pix = doc[i].get_pixmap(matrix=MAT, alpha=False)
        dest = OUT_DIR / name
        pix.save(dest.as_posix())
        doc.close()
        print(f"[ok] {dest.relative_to(ROOT)} <= {pdf.name} p{page_one_based}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
