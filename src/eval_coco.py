#!/usr/bin/env python
"""Per-class COCO evaluation for the layout-domain-shift experiment."""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

MODEL_LABELS = [
    "Caption", "Footnote", "Formula", "List-item", "Page-footer",
    "Page-header", "Picture", "Section-header", "Table", "Text", "Title",
    "Document Index", "Code", "Checkbox-Selected", "Checkbox-Unselected",
    "Form", "Key-Value Region",
]


def norm(name):
    return name.strip().lower().replace("_", "-").replace(" ", "-")


def load_predictions(path):
    with open(path) as f:
        blob = json.load(f)
    if isinstance(blob, dict):
        for key in ("predictions", "annotations", "results"):
            if key in blob:
                blob = blob[key]
                break
        else:
            sys.exit(f"{path}: dict with no predictions/annotations/results key")
    if not isinstance(blob, list) or not blob:
        sys.exit(f"{path}: expected a non-empty list of detection records")
    required = {"image_id", "category_id", "bbox", "score"}
    missing = required - set(blob[0])
    if missing:
        sys.exit(f"{path}: records missing required fields {sorted(missing)}")
    return blob


def check_bbox_format(preds, declared):
    sample = preds[: min(len(preds), 5000)]
    arr = np.array([p["bbox"] for p in sample], dtype=float)
    if declared == "xywh":
        bad = int((arr[:, 2:] <= 0).any(axis=1).sum())
        if bad:
            sys.exit(f"{bad}/{len(sample)} boxes have non-positive w or h. "
                     "Rerun with --bbox-format xyxy.")
    else:
        bad = int(((arr[:, 2] <= arr[:, 0]) | (arr[:, 3] <= arr[:, 1])).sum())
        if bad:
            sys.exit(f"{bad}/{len(sample)} boxes have x2<=x1 or y2<=y1. "
                     "Rerun with --bbox-format xywh.")


def to_xywh(bbox, declared):
    if declared == "xywh":
        return [float(v) for v in bbox]
    x1, y1, x2, y2 = (float(v) for v in bbox)
    return [x1, y1, x2 - x1, y2 - y1]


def build_label_map(coco, labels_are_coco_ids, verbose):
    gt_by_name = {norm(c["name"]): c["id"] for c in coco.dataset["categories"]}
    if labels_are_coco_ids:
        mapping = {cid: cid for cid in gt_by_name.values()}
        oos = {}
    else:
        mapping, oos = {}, {}
        for idx, name in enumerate(MODEL_LABELS):
            gt_id = gt_by_name.get(norm(name))
            if gt_id is None:
                oos[idx] = name
            else:
                mapping[idx] = gt_id
    if verbose:
        print("Label resolution (verify against model.config.id2label):")
        if labels_are_coco_ids:
            for name, cid in sorted(gt_by_name.items(), key=lambda kv: kv[1]):
                print(f"  gt id {cid:>2}  {name}")
        else:
            for idx, name in enumerate(MODEL_LABELS):
                target = mapping.get(idx)
                tag = f"gt id {target:>2}" if target is not None else "OUT OF SCHEMA"
                print(f"  model {idx:>2}  {name:<22} -> {tag}")
        print()
    if not labels_are_coco_ids and len(mapping) != len(gt_by_name):
        unmatched = set(gt_by_name) - {norm(MODEL_LABELS[i]) for i in mapping}
        sys.exit(f"Unmatched ground-truth classes: {sorted(unmatched)}. "
                 "Fix MODEL_LABELS before evaluating.")
    return mapping, oos


def select_images(coco, doc_category):
    if doc_category is None:
        return sorted(coco.getImgIds())
    ids = [img["id"] for img in coco.dataset["images"]
           if img.get("doc_category") == doc_category]
    if not ids:
        available = sorted({img.get("doc_category")
                            for img in coco.dataset["images"]} - {None})
        sys.exit(f"No images with doc_category={doc_category!r}. Present: {available}")
    return sorted(ids)


def per_class_metrics(ev, cat_ids, cat_names):
    out = {}
    for k, cid in enumerate(cat_ids):
        p = ev.eval["precision"][:, :, k, 0, 2]
        p50 = ev.eval["precision"][0, :, k, 0, 2]
        r = ev.eval["recall"][:, k, 0, 2]
        out[cat_names[cid]] = {
            "AP": float(np.mean(p[p > -1]) * 100) if (p > -1).any() else float("nan"),
            "AP50": float(np.mean(p50[p50 > -1]) * 100) if (p50 > -1).any() else float("nan"),
            "AR100": float(np.mean(r[r > -1]) * 100) if (r > -1).any() else float("nan"),
        }
    return out


def score(args):
    coco = COCO(args.gt)
    cat_names = {c["id"]: c["name"] for c in coco.dataset["categories"]}
    label_map, oos_labels = build_label_map(coco, args.labels_are_coco_ids,
                                            verbose=not args.quiet)
    img_ids = select_images(coco, args.doc_category)
    img_id_set = set(img_ids)

    preds = load_predictions(args.preds)
    check_bbox_format(preds, args.bbox_format)

    in_schema, oos_counts, kept_imgs = [], Counter(), set()
    dropped = 0
    for p in preds:
        if p["image_id"] not in img_id_set:
            dropped += 1
            continue
        if p["score"] < args.score_thresh:
            continue
        kept_imgs.add(p["image_id"])
        cid = p["category_id"]
        if cid in label_map:
            in_schema.append({
                "image_id": p["image_id"],
                "category_id": label_map[cid],
                "bbox": to_xywh(p["bbox"], args.bbox_format),
                "score": float(p["score"]),
            })
        else:
            oos_counts[oos_labels.get(cid, f"unmapped_{cid}")] += 1

    if not in_schema:
        sys.exit("No in-schema predictions survived filtering.")

    cat_ids = sorted(set(label_map.values()))
    ev = COCOeval(coco, coco.loadRes(in_schema), iouType="bbox")
    ev.params.imgIds = img_ids
    ev.params.catIds = cat_ids
    ev.evaluate()
    ev.accumulate()
    ev.summarize()

    total = len(in_schema) + sum(oos_counts.values())
    gt_counts = Counter(cat_names[a["category_id"]]
                        for a in coco.dataset["annotations"]
                        if a["image_id"] in img_id_set)

    result = {
        "split": args.split,
        "gt_file": str(args.gt),
        "pred_file": str(args.preds),
        "doc_category": args.doc_category,
        "score_thresh": args.score_thresh,
        "n_images": len(img_ids),
        "n_images_with_predictions": len(kept_imgs),
        "n_gt_annotations": sum(gt_counts.values()),
        "aggregate": {
            "mAP": float(ev.stats[0] * 100),
            "AP50": float(ev.stats[1] * 100),
            "AP75": float(ev.stats[2] * 100),
            "AP_small": float(ev.stats[3] * 100),
            "AP_medium": float(ev.stats[4] * 100),
            "AP_large": float(ev.stats[5] * 100),
        },
        "per_class": per_class_metrics(ev, cat_ids, cat_names),
        "gt_counts": dict(gt_counts),
        "out_of_schema": {
            "count": sum(oos_counts.values()),
            "rate": (sum(oos_counts.values()) / total) if total else 0.0,
            "by_class": {n: oos_counts.get(n, 0) for n in oos_labels.values()},
        },
        "predictions_dropped_image_not_in_split": dropped,
    }

    args.out.mkdir(parents=True, exist_ok=True)
    json_path = args.out / f"{args.split}.json"
    csv_path = args.out / f"{args.split}_per_class.csv"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "gt_instances", "AP", "AP50", "AR100"])
        for name, m in sorted(result["per_class"].items()):
            w.writerow([name, gt_counts.get(name, 0),
                        f"{m['AP']:.1f}", f"{m['AP50']:.1f}", f"{m['AR100']:.1f}"])

    oos = result["out_of_schema"]
    print(f"\nsplit: {args.split}")
    print(f"mAP {result['aggregate']['mAP']:.1f}  AP50 {result['aggregate']['AP50']:.1f}")
    print(f"Out-of-schema: {oos['count']} predictions, {oos['rate']*100:.0f}% of kept output")
    for name, n in sorted(oos["by_class"].items(), key=lambda kv: -kv[1]):
        share = (n / oos["count"] * 100) if oos["count"] else 0.0
        print(f"  {name:<22} {n:>8}  ({share:.0f}% of OOS)")
    print(f"\nWrote {json_path}\nWrote {csv_path}")


def compare(args):
    blobs = []
    for p in args.results:
        with open(p) as f:
            blobs.append(json.load(f))
    base = blobs[0]
    names = sorted(base["per_class"])
    cols = [b["split"] for b in blobs]

    def cell(v):
        return "n/a" if v != v else f"{v:.1f}"

    header = ["class", "gt_n (" + cols[0] + ")"] + cols
    if len(blobs) > 1:
        header += [f"delta {c} vs {cols[0]}" for c in cols[1:]]
    rows = []
    for name in names:
        vals = [b["per_class"].get(name, {}).get("AP", float("nan")) for b in blobs]
        row = [name, str(base["gt_counts"].get(name, 0))] + [cell(v) for v in vals]
        for v in vals[1:]:
            d = v - vals[0]
            row.append("n/a" if d != d else f"{d:+.1f}")
        rows.append(row)
    agg = [b["aggregate"]["mAP"] for b in blobs]
    row = ["mAP (all)", str(base["n_gt_annotations"])] + [cell(v) for v in agg]
    for v in agg[1:]:
        row.append(f"{v - agg[0]:+.1f}")
    rows.append(row)

    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(header)]

    def line(cells):
        return "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells)) + " |"

    print(line(header))
    print("|" + "|".join("-" * (w + 2) for w in widths) + "|")
    for r in rows:
        print(line(r))
    print()
    for b in blobs:
        oos = b["out_of_schema"]
        print(f"{b['split']}: out-of-schema {oos['count']} "
              f"({oos['rate']*100:.0f}% of output), images {b['n_images']}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)

    s = sub.add_parser("score")
    s.add_argument("--gt", type=Path, required=True)
    s.add_argument("--preds", type=Path, required=True)
    s.add_argument("--split", required=True)
    s.add_argument("--doc-category", default=None)
    s.add_argument("--score-thresh", type=float, default=0.0)
    s.add_argument("--bbox-format", choices=["xywh", "xyxy"], default="xywh")
    s.add_argument("--labels-are-coco-ids", action="store_true")
    s.add_argument("--out", type=Path, default=Path("results"))
    s.add_argument("--quiet", action="store_true")
    s.set_defaults(func=score)

    c = sub.add_parser("compare")
    c.add_argument("results", nargs="+", type=Path)
    c.set_defaults(func=compare)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
