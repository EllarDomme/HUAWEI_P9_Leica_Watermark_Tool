#!/usr/bin/env python3
"""从参考图里切出单个字形，供后续做成字体。

流程：
1. 二值化（白字黑底）
2. 按水平投影切出文字行
3. 每行按竖直投影切出字符块（空白列分隔）
4. 每个字符块裁出 bbox，存成灰度 PNG + 记录尺寸

用法：python extract_glyphs.py <图片> <输出目录>
"""
import os
import sys
import json

import cv2
import numpy as np


def load_mask(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit('cannot read ' + path)
    # 自动判断极性：亮底则反相，保证字是白的
    if (img > 140).mean() > 0.5:
        img = 255 - img
    _, mask = cv2.threshold(img, 120, 255, cv2.THRESH_BINARY)
    return img, mask


def row_bands(mask, min_gap=3, min_height=8):
    rows = (mask > 0).sum(axis=1)
    active = rows > 0
    bands = []
    start = None
    gap = 0
    for y, a in enumerate(active):
        if a:
            if start is None:
                start = y
            gap = 0
        else:
            if start is not None:
                gap += 1
                if gap >= min_gap:
                    if y - gap - start + 1 >= min_height:
                        bands.append((start, y - gap))
                    start = None
                    gap = 0
    if start is not None and len(active) - start >= min_height:
        bands.append((start, len(active) - 1))
    return bands


def char_blocks(mask, y0, y1, min_gap=2, min_width=2):
    band = mask[y0:y1 + 1]
    cols = (band > 0).sum(axis=0)
    active = cols > 0
    blocks = []
    start = None
    gap = 0
    for x, a in enumerate(active):
        if a:
            if start is None:
                start = x
            gap = 0
        else:
            if start is not None:
                gap += 1
                if gap >= min_gap:
                    if x - gap - start + 1 >= min_width:
                        blocks.append((start, x - gap))
                    start = None
                    gap = 0
    if start is not None:
        blocks.append((start, len(active) - 1))
    return blocks


def main():
    if len(sys.argv) < 3:
        raise SystemExit('usage: extract_glyphs.py <image> <outdir>')
    path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    img, mask = load_mask(path)
    if len(sys.argv) > 3:
        left = int(sys.argv[3])
        mask[:, :left] = 0

    bands = row_bands(mask)
    print('rows:', len(bands))
    meta = []
    for i, (y0, y1) in enumerate(bands):
        blocks = char_blocks(mask, y0, y1)
        print('  row %d  y=%d..%d  h=%d  blocks=%d  widths=%s' %
              (i, y0, y1, y1 - y0 + 1, len(blocks), [b[1] - b[0] + 1 for b in blocks][:14]))
        for j, (x0, x1) in enumerate(blocks):
            crop = mask[y0:y1 + 1, x0:x1 + 1]
            # 去掉全空边缘
            ys, xs = np.where(crop > 0)
            if not len(xs):
                continue
            crop = crop[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            name = 'r%02d_c%03d.png' % (i, j)
            cv2.imwrite(os.path.join(outdir, name), crop)
            meta.append({'file': name, 'row': i, 'col': j,
                         'w': int(crop.shape[1]), 'h': int(crop.shape[0]),
                         'y0': int(y0), 'x0': int(x0)})
    with open(os.path.join(outdir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print('glyph crops:', len(meta))


if __name__ == '__main__':
    main()
