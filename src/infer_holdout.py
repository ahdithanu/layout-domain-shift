#!/usr/bin/env python
"""Run the docling-layout RT-DETR checkpoint over the holdout pages."""
import argparse, json
from pathlib import Path

import torch
from PIL import Image
from transformers import RTDetrForObjectDetection, RTDetrImageProcessor

MODEL = "HuggingPanda/docling-layout"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True, help="holdout COCO json (for image ids)")
    ap.add_argument("--images", required=True, help="directory of page PNGs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--thresh", type=float, default=0.0)
    a = ap.parse_args()

    gt = json.load(open(a.gt))
    id_by_name = {im["file_name"]: im["id"] for im in gt["images"]}

    proc = RTDetrImageProcessor.from_pretrained(MODEL)
    model = RTDetrForObjectDetection.from_pretrained(MODEL)
    model.eval()
    print("id2label:", model.config.id2label)

    preds = []
    for name, img_id in sorted(id_by_name.items()):
        path = Path(a.images) / name
        if not path.exists():
            raise SystemExit(f"missing image: {path}")
        img = Image.open(path).convert("RGB")
        inputs = proc(images=img, return_tensors="pt", size={"height": 640, "width": 640})
        with torch.no_grad():
            out = model(**inputs)
        res = proc.post_process_object_detection(
            out, target_sizes=torch.tensor([[img.height, img.width]]),
            threshold=a.thresh)[0]
        for score, label, box in zip(res["scores"], res["labels"], res["boxes"]):
            x1, y1, x2, y2 = [float(v) for v in box]
            preds.append({
                "image_id": img_id,
                "category_id": int(label),
                "bbox": [x1, y1, x2 - x1, y2 - y1],
                "score": float(score),
            })
        print(f"  {name}: {len(res['scores'])} detections")

    json.dump(preds, open(a.out, "w"))
    print(f"\n{len(preds)} predictions over {len(id_by_name)} images -> {a.out}")


if __name__ == "__main__":
    main()
