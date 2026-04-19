#!/usr/bin/env python3
"""
从 content_manifest.yaml 读取 pdf_image_exports，使用 pypdf 导出内嵌位图到 interview_assets/extracted/。
用法（在项目根目录）: python3 tools/pdf_extract/extract_assets.py
依赖: pip install -r requirements.txt（含 PyYAML、pypdf、Pillow）
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from pypdf import PdfReader


def load_manifest(root: Path) -> dict:
    path = root / "content_manifest.yaml"
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise SystemExit("需要 PyYAML：pip install pyyaml，或在 extract_assets 中改用最小 JSON manifest。")
    return yaml.safe_load(text)


def export_one(reader: PdfReader, page_1based: int, image_index_1based: int) -> bytes:
    page = reader.pages[page_1based - 1]
    imgs = page.images
    if not imgs:
        raise ValueError(f"第 {page_1based} 页无内嵌图片")
    if image_index_1based < 1 or image_index_1based > len(imgs):
        raise ValueError(f"第 {page_1based} 页仅有 {len(imgs)} 张图，请求索引 {image_index_1based}")
    img = imgs[image_index_1based - 1]
    pil = img.image
    import io

    buf = io.BytesIO()
    # 统一 PNG，便于网页引用
    pil.save(buf, format="PNG")
    return buf.getvalue()


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    data = load_manifest(root)
    exports = data.get("pdf_image_exports") or []
    out_dir = root / "interview_assets" / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for item in exports:
        out_name = item["out"]
        rel = item["pdf"]
        page = int(item["page"])
        idx = int(item["image_index"])
        pdf_path = root / rel
        if not pdf_path.exists():
            print(f"[skip] 文件不存在: {rel}", file=sys.stderr)
            continue
        reader = PdfReader(str(pdf_path))
        try:
            png_bytes = export_one(reader, page, idx)
        except Exception as e:
            print(f"[fail] {out_name} <- {rel} p{page} i{idx}: {e}", file=sys.stderr)
            continue
        dest = out_dir / f"{out_name}.png"
        dest.write_bytes(png_bytes)
        written.append(str(dest.relative_to(root)))
        print(f"[ok] {dest.relative_to(root)}")

    index_path = out_dir / "_extract_index.txt"
    index_path.write_text("\n".join(written) + "\n", encoding="utf-8")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
