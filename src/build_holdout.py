#!/usr/bin/env python
"""Render holdout pages to PNG and record mechanical page properties."""

import argparse
import csv
from pathlib import Path

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

DPI = 150
WORD_MIN = 50
WORDS_PER_INK_MIN = 0.02


def page_features(page):
    words = len(page.get_text("words"))
    pix = page.get_pixmap(dpi=50)
    ink = sum(1 for b in pix.samples if b < 240)
    drawings = page.get_drawings()
    n_vec = sum(1 for d in drawings for it in d["items"] if it[0] in ("l", "re"))
    return {
        "words": words,
        "ink_px": ink,
        "n_images": len(page.get_images()),
        "n_vec": n_vec,
        "width_pt": round(page.rect.width),
        "height_pt": round(page.rect.height),
        "orientation": "landscape" if page.rect.width > page.rect.height else "portrait",
    }


def classify(f):
    if f["words"] == 0 and f["ink_px"] == 0:
        return "blank"
    if f["words"] == 0:
        return "scanned"
    ratio = f["words"] / max(f["ink_px"], 1) * 1000
    if f["words"] < WORD_MIN or ratio < WORDS_PER_INK_MIN:
        return "image_dominant"
    return "native"


def inspect(args):
    doc = pymupdf.open(args.pdf)
    print(f"{args.pdf}  ({doc.page_count} pages)")
    print(f"{'pg':>4} {'class':<15} {'words':>6} {'ink':>8} {'vec':>5} {'img':>4} {'orient':>10}")
    for i, page in enumerate(doc, 1):
        f = page_features(page)
        print(f"{i:>4} {classify(f):<15} {f['words']:>6} {f['ink_px']:>8} "
              f"{f['n_vec']:>5} {f['n_images']:>4} {f['orientation']:>10}")


def render(args):
    doc = pymupdf.open(args.pdf)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pages = [int(p) for p in args.pages.split(",")]
    manifest = out / "manifest.csv"
    new = not manifest.exists()
    with open(manifest, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow([
                "image_file", "doc_id", "stratum", "source_pdf", "page_no",
                "text_layer_class", "words", "ink_px", "n_vec", "n_images",
                "width_pt", "height_pt", "orientation", "png_w", "png_h",
            ])
        for pno in pages:
            page = doc[pno - 1]
            f = page_features(page)
            cls = classify(f)
            if cls == "blank":
                print(f"  SKIP page {pno}: blank")
                continue
            name = f"{args.doc_id}_p{pno:03d}.png"
            pix = page.get_pixmap(dpi=DPI)
            pix.save(out / name)
            w.writerow([
                name, args.doc_id, args.stratum, Path(args.pdf).name, pno,
                cls, f["words"], f["ink_px"], f["n_vec"], f["n_images"],
                f["width_pt"], f["height_pt"], f["orientation"],
                pix.width, pix.height,
            ])
            print(f"  {name}  {cls}  {pix.width}x{pix.height}")
    print(f"\nmanifest: {manifest}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    i = sub.add_parser("inspect")
    i.add_argument("pdf")
    i.set_defaults(func=inspect)
    r = sub.add_parser("render")
    r.add_argument("pdf")
    r.add_argument("--doc-id", required=True)
    r.add_argument("--stratum", required=True)
    r.add_argument("--pages", required=True, help="comma separated, 1-indexed")
    r.add_argument("--out", default="data/holdout")
    r.set_defaults(func=render)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
