#!/usr/bin/env python3
"""把参考图里切出的字形块按形状聚类，同一字符归为一簇。

用法：python cluster_glyphs.py <图片> <左裁切> [输出目录]
输出：
  clusters/  每簇的代表图（最大的那个样本）
  sheet.png  总览图，带簇编号和样本数
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
    if (img > 140).mean() > 0.5:
        img = 255 - img
    _, mask = cv2.threshold(img, 120, 255, cv2.THRESH_BINARY)
    return mask


def row_bands(mask, min_gap=3, min_height=8):
    rows = (mask > 0).sum(axis=1)
    active = rows > 0
    bands, start, gap = [], None, 0
    for y, a in enumerate(active):
        if a:
            if start is None:
                start = y
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= min_gap:
                if y - gap - start + 1 >= min_height:
                    bands.append((start, y - gap))
                start, gap = None, 0
    if start is not None:
        bands.append((start, len(active) - 1))
    return bands


def char_blocks(mask, y0, y1, min_gap=2, min_width=2):
    band = mask[y0:y1 + 1]
    cols = (band > 0).sum(axis=0)
    active = cols > 0
    blocks, start, gap = [], None, 0
    for x, a in enumerate(active):
        if a:
            if start is None:
                start = x
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= min_gap:
                if x - gap - start + 1 >= min_width:
                    blocks.append((start, x - gap))
                start, gap = None, 0
    if start is not None:
        blocks.append((start, len(active) - 1))
    return blocks


def collect(mask, left=0):
    out = []
    for y0, y1 in row_bands(mask):
        for x0, x1 in char_blocks(mask, y0, y1):
            if x1 <= left:
                continue
            crop = mask[y0:y1 + 1, x0:x1 + 1]
            ys, xs = np.where(crop > 0)
            if not len(xs):
                continue
            crop = crop[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            if crop.shape[0] < 12 or crop.shape[1] < 3:
                continue
            out.append(crop)
    return out


def feature(crop, size=48):
    h, w = crop.shape
    s = size / max(h, w)
    r = cv2.resize(crop, (max(1, int(round(w * s))), max(1, int(round(h * s)))), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((size, size), np.uint8)
    y0 = (size - r.shape[0]) // 2
    x0 = (size - r.shape[1]) // 2
    canvas[y0:y0 + r.shape[0], x0:x0 + r.shape[1]] = r
    return canvas.astype(np.float32) / 255.0


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: cluster_glyphs.py <image> [left] [outdir]')
    path = sys.argv[1]
    left = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    outdir = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(path)[0] + '_clusters'
    os.makedirs(outdir, exist_ok=True)

    mask = load_mask(path)
    if left:
        mask[:, :left] = 0
    crops = collect(mask)
    print('glyphs:', len(crops))

    reps = []          # 代表图
    groups = []        # 每簇成员
    for c in crops:
        f = feature(c)
        best, bestd = -1, 1e9
        for i, rf in enumerate(reps):
            d = float(np.abs(f - rf).mean())
            if d < bestd:
                bestd, best = d, i
        if best >= 0 and bestd < 0.16:
            groups[best].append(c)
            if c.size > groups[best][0].size * len(groups[best]):
                pass
        else:
            reps.append(f)
            groups.append([c])

    print('clusters:', len(groups))
    order = sorted(range(len(groups)), key=lambda i: -len(groups[i]))

    # 代表图取成员中面积最大的
    tiles = []
    report = []
    for i in order:
        members = groups[i]
        rep = max(members, key=lambda c: c.shape[0] * c.shape[1])
        p = os.path.join(outdir, 'cluster_%02d.png' % i)
        cv2.imwrite(p, rep)
        report.append({'id': i, 'count': len(members), 'w': int(rep.shape[1]), 'h': int(rep.shape[0])})
        tiles.append((i, len(members), rep))

    # 总览
    cell = 120
    cols = 8
    rows = (len(tiles) + cols - 1) // cols
    sheet = np.full((rows * cell + 20, cols * cell, 3), 18, np.uint8)
    cv2.putText(sheet, 'clusters', (10, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    for k, (i, n, rep) in enumerate(tiles):
        r, c = divmod(k, cols)
        y, x = 20 + r * cell, c * cell
        h, w = rep.shape
        s = min((cell - 30) / h, (cell - 30) / w, 1.6)
        small = cv2.resize(rep, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
        hh, ww = small.shape
        sheet[y + 22:y + 22 + hh, x + (cell - ww) // 2:x + (cell - ww) // 2 + ww] = cv2.cvtColor(small, cv2.COLOR_GRAY2BGR)
        cv2.putText(sheet, '%d (%d)' % (i, n), (x + 6, y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 200, 255), 1)
    cv2.imwrite(os.path.join(outdir, 'sheet.png'), sheet)
    with open(os.path.join(outdir, 'clusters.json'), 'w') as f:
        json.dump(report, f, indent=1)
    print('wrote', os.path.join(outdir, 'sheet.png'))


if __name__ == '__main__':
    main()
