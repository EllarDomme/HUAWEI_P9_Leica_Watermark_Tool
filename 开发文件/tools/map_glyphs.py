#!/usr/bin/env python3
"""按已知文字把切出的字块逐字对位，收集每个字符的所有样本。

用法：python map_glyphs.py <图片> <左裁切> <列宽> <输出目录>
（文字表写在 ROWS 里）
"""
import os
import sys
import json

import cv2
import numpy as np

from cluster_glyphs import load_mask, row_bands, char_blocks

P9_ROWS = [
    "HUAWEIP9",
    "LEICADUALCAMERA",
    "HUAWEIP9Plus",
    "LEICADUALCAMERA",
    "HUAWEIP10",
    "LEICADUALCAMERA",
    "HUAWEIP10Plus",
    "LEICADUALSUMMILUX",
    "HUAWEIP20",
    "LEICADUALCAMERA|AI",
    "HUAWEIP20Pro",
    "LEICATRIPLECAMERA|AI",
    "HUAWEIP30",
    "LEICATRIPLECAMERA",
    "HUAWEIP30Pro",
    "LEICAQUADCAMERA",
    "HUAWEIP405G",
    "UltraVisionLEICATripleCamera",
    "HUAWEIP40Pro5G",
    "UltraVisionLEICAQuadCamera",
    "HUAWEIP40Pro+5G",
    "UltraVisionLEICAPentaCamera",
    "HUAWEIP50",
    "Dual-MatrixCamera",
    "HUAWEIP50Pro",
    "Dual-MatrixCamera",
]

SHEET_ROWS = ["01234", "56789", "SUMILXPH", "LECA/.:-"]

MATE_LEFT = [
    "HUAWEIMate9", "LEICADUALCAMERA",
    "HUAWEIMate9Pro", "LEICADUALCAMERA",
    "PORSCHEDESIGN|HUAWEIMate9", "LEICADUALCAMERA",
    "HUAWEIMate10", "NEWLEICADUALCAMERA",
    "HUAWEIMate10Pro", "NEWLEICADUALCAMERA",
    "PORSCHEDESIGN", "HUAWEIMate10",
    "PORSCHEDESIGN", "HUAWEIMateRS",
    "HUAWEIMateX", "LEICAQUADCAMERA",
    "HUAWEIMateXs", "LEICAQUADCAMERA",
    "HUAWEIMateX2", "UltraVisionCamera|LEICA",
]

MATE_RIGHT = [
    "HUAWEIMate20", "LEICATRIPLECAMERA|AI",
    "HUAWEIMate20Pro", "LEICATRIPLECAMERA|AI",
    "PORSCHEDESIGN", "HUAWEIMate20RS",
    "HUAWEIMate20X", "LEICATRIPLECAMERA|AI",
    "HUAWEIMate30", "SuperSensingCamera|LEICA",
    "HUAWEIMate30Pro", "SuperSensingCineCamera|LEICA",
    "PORSCHEDESIGN", "HUAWEIMate30RS",
    "HUAWEIMate40", "UltraVisionCamera|LEICA",
    "HUAWEIMate40Pro", "UltraVisionCineCamera|LEICA",
    "HUAWEIMate40Pro+", "UltraVisionCineCamera|LEICA",
    "PORSCHEDESIGN", "HUAWEIMate40RS",
]


def harvest(mask, rows, outdir, tag):
    bands = row_bands(mask)
    if len(bands) != len(rows):
        print('!! row mismatch: found %d, expected %d' % (len(bands), len(rows)))
    got = {}
    used = 0
    for i, (y0, y1) in enumerate(bands):
        blocks = char_blocks(mask, y0, y1)
        text = rows[i] if i < len(rows) else None
        if text is None:
            continue
        if len(blocks) != len(text):
            print('   row %d: blocks %d != chars %d  (%s)' % (i, len(blocks), len(text), text[:30]))
            continue
        for j, (x0, x1) in enumerate(blocks):
            crop = mask[y0:y1 + 1, x0:x1 + 1]
            ys, xs = np.where(crop > 0)
            if not len(xs):
                continue
            crop = crop[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            ch = text[j]
            if ch == ' ':
                continue
            d = os.path.join(outdir, 'by-char')
            os.makedirs(d, exist_ok=True)
            fn = '%s_%03d.png' % (ch if ch.isalnum() else 'sym%02x' % ord(ch), used)
            used += 1
            cv2.imwrite(os.path.join(d, fn), crop)
            got.setdefault(ch, []).append(fn)
    return got


def main():
    if len(sys.argv) < 4:
        raise SystemExit('usage: map_glyphs.py <image> <left> <colwidth|0> <outdir>')
    path, left, colw, outdir = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    os.makedirs(outdir, exist_ok=True)
    mask = load_mask(path)
    total = {}
    if colw:
        h, w = mask.shape
        mid = w // 2
        left_half = mask[:, :mid].copy()
        right_half = mask[:, mid:].copy()
        if left:
            left_half[:, :left] = 0
            right_half[:, :left] = 0
        if path.endswith('hv-mate-series.jpg'):
            g1 = harvest(left_half, MATE_LEFT, os.path.join(outdir, 'L'), 'L')
            g2 = harvest(right_half, MATE_RIGHT, os.path.join(outdir, 'R'), 'R')
        else:
            g1, g2 = {}, {}
        for g in (g1, g2):
            for k, v in g.items():
                total.setdefault(k, []).extend(v)
    else:
        if left:
            mask[:, :left] = 0
        if path.endswith('hv-p9-series.jpg'):
            rows = P9_ROWS
        elif path.endswith('leica-glyph-sheet.png'):
            rows = SHEET_ROWS
        else:
            rows = []
        total = harvest(mask, rows, outdir, 'all')

    print('chars found:', len(total))
    summary = {k: len(v) for k, v in sorted(total.items())}
    print(json.dumps(summary, ensure_ascii=False))
    with open(os.path.join(outdir, 'by-char-map.json'), 'w') as f:
        json.dump({k: v for k, v in total.items()}, f, indent=1)


if __name__ == '__main__':
    main()
