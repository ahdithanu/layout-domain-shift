#!/usr/bin/env python
"""Normalize a Label Studio COCO export to the DocLayNet category id space."""
import argparse, json, re
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ls-json", required=True)
    ap.add_argument("--doclaynet-val", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    ls = json.load(open(a.ls_json))
    gt = json.load(open(a.doclaynet_val))
    canon = {c["name"].strip().lower(): c["id"] for c in gt["categories"]}

    remap = {}
    for c in ls["categories"]:
        key = c["name"].strip().lower()
        if key not in canon:
            raise SystemExit(f"category {c['name']!r} not in DocLayNet schema")
        remap[c["id"]] = canon[key]

    for im in ls["images"]:
        stem = Path(im["file_name"]).name
        im["file_name"] = re.sub(r"^[0-9a-f]{8}-", "", stem)

    for an in ls["annotations"]:
        an["category_id"] = remap[an["category_id"]]
        an.setdefault("iscrowd", 0)
        x, y, w, h = an["bbox"]
        an["area"] = float(w) * float(h)

    ls["categories"] = [{"id": v, "name": k} for k, v in sorted(canon.items(), key=lambda kv: kv[1])]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(ls, open(a.out, "w"))
    print(f"{len(ls['images'])} images, {len(ls['annotations'])} annotations -> {a.out}")


if __name__ == "__main__":
    main()
