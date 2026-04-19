#!/usr/bin/env python3
"""将指定 PDF 中每一页的内嵌位图全部导出为 PNG（pypdf）。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from pypdf import PdfReader

# 相对项目根：与幻灯片相关的素材 PDF（可按需增删）
PDFS_REL = [
    "新素材/项目经历.pdf",
    "新素材/Vertical AI research/旅行记忆/旅行记忆总文档.pdf",
    "新素材/Vertical AI research/NLU模型训练上板/AI notes_ Discussion on Model Quantization, Conversion and Data Provision on Apr 16, 2026.pdf",
    "新素材/Vertical AI research/NLU模型训练上板/NLU 自动标注样本分布统计.pdf",
    "新素材/Vertical AI research/Ai 代驾/AI代驾原型演示及Readme文档 2025年10月7日.pdf",
    "新素材/Vertical AI research/Ai 代驾/AI 代驾数据集接入 VLMEvalKit 开发文档.pdf",
    "新素材/Vertical AI research/Ai 代驾/智能纪要：AI代驾原型演示 2025年10月7日.pdf",
    "新素材/Paper submission Structured Runtime Safety Monitoring for Camera-Based Driver Monitoring Systems/ITSC26_0759_MS.pdf",
    "新素材/Horizontal AI application/我作为导师带领的实习生周会纪要，包含各种探索项目/AI notes_ 01-16 | RD3 26S Intern Weekly Meeting on Jan 16, 2026.pdf",
    "新素材/Horizontal AI application/PRD-UIUX文档比对工具/智能纪要：Figma工作流及AI应用会议 2026年3月30日.pdf",
    "新素材/Horizontal AI application/PRD-UIUX文档比对工具/智能纪要：AI文档比对_内部团队交流 2026年3月23日.pdf",
    "新素材/Horizontal AI application/获奖项目人才 365，晋升依据/《AI Hackathon大赛》051简历筛选.pdf",
    "新素材/Legacy CV perception project/行车底图预标模型实验记录.pdf",
    "新素材/Legacy CV perception project/Weekly Progress Update - Bowen.pdf",
    "新素材/Innovus capital 创业/想法.pdf",
]


def slugify(rel: str) -> str:
    base = Path(rel).stem
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", base, flags=re.UNICODE)
    s = s.strip("_")[:80]
    return s or "doc"


def export_pdf(root: Path, rel: str, out_root: Path) -> int:
    pdf_path = root / rel
    if not pdf_path.exists():
        print(f"[skip] missing: {rel}", file=sys.stderr)
        return 0
    slug = slugify(rel)
    dest_dir = out_root / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(pdf_path))
    n = 0
    for pi, page in enumerate(reader.pages):
        for ii, img in enumerate(page.images):
            n += 1
            pil = img.image
            name = f"p{pi + 1:03d}_i{ii + 1:02d}.png"
            dest = dest_dir / name
            pil.save(dest, format="PNG")
    print(f"[ok] {rel} -> {dest_dir.relative_to(root)} ({n} imgs)")
    return n


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    out_root = root / "interview_assets" / "extracted_all"
    out_root.mkdir(parents=True, exist_ok=True)
    total = 0
    for rel in PDFS_REL:
        total += export_pdf(root, rel, out_root)
    print(f"total images: {total}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
