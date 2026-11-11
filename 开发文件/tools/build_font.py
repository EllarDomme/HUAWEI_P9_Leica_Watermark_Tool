#!/usr/bin/env python3
"""从高清素材里提取字形并生成字体（HWLeica）。

配置里每张图：
  path    图片路径
  cols    是否左右两栏（True/False）
  rows    逐行文字（不含空格）；分栏时 rows 为 (左栏行, 右栏行)

流程：切行 → 切字 → 按文字对位 → 每字符取像素最高的样本 →
      轮廓化（中点二次曲线）→ 组字体。
"""
import os
import sys
import json
import glob

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

EM = 1000
CAP = 700
GAP = 0.135
EPS = 1.6          # 轮廓简化（像素）

SRC_DIR = r"E:\DeskTop\字体素材"
OUT_DIR = r"D:\P9徕卡水印工具\开发文件\fonts"

SHEET = ["01234", "56789", "SUMILXPH", "LECA/.:-"]

P9 = [
    "HUAWEIP9", "LEICADUALCAMERA",
    "HUAWEIP9Plus", "LEICADUALCAMERA",
    "HUAWEIP10", "LEICADUALCAMERA",
    "HUAWEIP10Plus", "LEICADUALSUMMILUX",
    "HUAWEIP20", "LEICADUALCAMERA|AI",
    "HUAWEIP20Pro", "LEICATRIPLECAMERA|AI",
]

P3050 = [
    "HUAWEIP30", "LEICATRIPLECAMERA",
    "HUAWEIP30Pro", "LEICAQUADCAMERA",
    "HUAWEIP405G", "UltraVisionLEICATripleCamera",
    "HUAWEIP40Pro5G", "UltraVisionLEICAQuadCamera",
    "HUAWEIP40Pro+5G", "UltraVisionLEICAPentaCamera",
    "HUAWEIP50", "Dual-MatrixCamera",
    "HUAWEIP50Pro", "Dual-MatrixCamera",
]

MATE920_L = [
    "HUAWEIMate9", "LEICADUALCAMERA",
    "HUAWEIMate9Pro", "LEICADUALCAMERA",
    "PORSCHEDESIGN|HUAWEIMate9", "LEICADUALCAMERA",
]
MATE920_R = [
    "HUAWEIMate20", "LEICATRIPLECAMERA|AI",
    "HUAWEIMate20Pro", "LEICATRIPLECAMERA|AI",
    "PORSCHEDESIGN", "HUAWEIMate20RS",
    "HUAWEIMate20X", "LEICATRIPLECAMERA|AI",
]

MATE1030_L = [
    "HUAWEIMate10", "NEWLEICADUALCAMERA",
    "HUAWEIMate10Pro", "NEWLEICADUALCAMERA",
    "PORSCHEDESIGN|", "HUAWEIMate10",
    "PORSCHEDESIGN", "HUAWEIMateRS",
]
MATE1030_R = [
    "HUAWEIMate30", "SuperSensingCamera|LEICA",
    "HUAWEIMate30Pro", "SuperSensingCineCamera|LEICA",
    "PORSCHEDESIGN|", "HUAWEIMate30RS",
]

MATEX40_L = [
    "HUAWEIMateX", "LEICAQUADCAMERA",
    "HUAWEIMateXs", "LEICAQUADCAMERA",
    "HUAWEIMateX2", "UltraVisionCamera|LEICA",
]
MATEX40_R = [
    "HUAWEIMate40", "UltraVisionCamera|LEICA",
    "HUAWEIMate40Pro", "UltraVisionCineCamera|LEICA",
    "HUAWEIMate40Pro+", "UltraVisionCineCamera|LEICA",
    "PORSCHEDESIGN|", "HUAWEIMate40RS",
]

CONFIG = [
    dict(path="20261111-193341.png", cols=False, rows=SHEET),
    dict(path="20261111-194103.png", cols=False, rows=P9),
    dict(path="20261111-194315.png", cols=False, rows=P3050),
    dict(path="20261111-194647.png", cols=True, rows=(MATE920_L, MATE920_R)),
    dict(path="20261111-194830.png", cols=True, rows=(MATE1030_L, MATE1030_R)),
    dict(path="20261111-195019.png", cols=True, rows=(MATEX40_L, MATEX40_R)),
]


def mask_of(path):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        raise SystemExit('cannot read ' + path)
    im = cv2.GaussianBlur(im, (3, 3), 0)
    _, m = cv2.threshold(im, 150, 255, cv2.THRESH_BINARY)
    return im, m


def rows_of(m, min_gap=8, min_h=30):
    act = (m > 0).sum(axis=1) > 0
    out, start, gap = [], None, 0
    for y, a in enumerate(act):
        if a:
            if start is None:
                start = y
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= min_gap:
                if y - gap - start + 1 >= min_h:
                    out.append((start, y - gap))
                start, gap = None, 0
    if start is not None and len(act) - start >= min_h:
        out.append((start, len(act) - 1))
    return out


def cols_of(m, y0, y1, min_gap=6, min_w=6):
    band = m[y0:y1 + 1]
    act = (band > 0).sum(axis=0) > 0
    out, start, gap = [], None, 0
    for x, a in enumerate(act):
        if a:
            if start is None:
                start = x
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= min_gap:
                if x - gap - start + 1 >= min_w:
                    out.append((start, x - gap))
                start, gap = None, 0
    if start is not None and len(act) - start >= min_w:
        out.append((start, len(act) - 1))
    return out



def comp_blocks(m, y0, y1):
    """连通域分组：同一竖线上的笔画合并；返回 (x0, x1, w, h)"""
    band = m[y0:y1 + 1]
    bh = y1 - y0 + 1
    n, labels, stats, _ = cv2.connectedComponentsWithStats((band > 0).astype(np.uint8), 8)
    boxes = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 40 and h < 0.35 * bh:
            continue
        boxes.append([x, x + w - 1, w, h])
    boxes.sort()
    merged = []
    for b in boxes:
        if merged and b[0] <= merged[-1][1] + 3:
            merged[-1][1] = max(merged[-1][1], b[1])
            merged[-1][2] = merged[-1][1] - merged[-1][0] + 1
            merged[-1][3] = max(merged[-1][3], b[3])
        else:
            merged.append(list(b))
    # 去掉行首的图标（近正方形）
    while merged and merged[0][2] > 0.72 * merged[0][3] and merged[0][3] > 0.8 * bh:
        merged.pop(0)
    return [(a, b) for a, b, w, h in merged]

def best_blocks(m, y0, y1, want):
    for gap in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12):
        blocks = cols_of(m, y0, y1, min_gap=gap)
        if len(blocks) == want:
            return blocks
    return None


def best_rows(m, want):
    for gap in (3, 4, 5, 6, 7, 8, 10, 12):
        bands = rows_of(m, min_gap=gap)
        if len(bands) == want:
            return bands
    return None


def harvest(image, text_rows, crops, tag, x_off=0):
    im, m = mask_of(image)
    bands = best_rows(m, len(text_rows))
    if bands is None:
        bands = rows_of(m)
        print('  [%s] rows %d != text %d（按现有行处理）' % (tag, len(bands), len(text_rows)))
    if len(bands) < len(text_rows):
        print('  [%s] rows %d < text %d' % (tag, len(bands), len(text_rows)))
    # 先估这张图的大写字高：取所有 block 高度的中位数
    est = []
    for i, band in enumerate(bands):
        if i >= len(text_rows):
            break
        for x0, x1 in cols_of(m, band[0], band[1], min_gap=4):
            est.append(x1 - x0 + 1)
    cap_h = float(np.median(est)) if est else 60.0

    hits = 0
    caps = []
    for i, band in enumerate(bands):
        if i >= len(text_rows):
            break
        text = text_rows[i]
        y0, y1 = band
        blocks = comp_blocks(m, y0, y1)
        if len(blocks) != len(text):
            print('  [%s] row %d 切分不匹配（%d vs %d）：%s' % (tag, i, len(blocks), len(text), text[:26]))
            continue
        for j, ch in enumerate(text):
            x0, x1 = blocks[j]
            crop = m[y0:y1 + 1, x0:x1 + 1]
            ys, xs = np.where(crop > 0)
            if not len(xs):
                continue
            crop = crop[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            if crop.shape[0] < 0.12 * cap_h:
                continue
            if ch.isupper():
                caps.append(int(crop.shape[0]))
            crops.setdefault(ch, []).append((int(crop.shape[0]), crop, cap_h))
            hits += 1
    return hits


def trace(crop, cap_px):
    h, w = crop.shape
    k = CAP / float(cap_px)
    contours, hierarchy = cv2.findContours(crop, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hierarchy is None:
        return [], 0.0
    out = []
    for i, c in enumerate(contours):
        if cv2.contourArea(c) < 3:
            continue
        approx = cv2.approxPolyDP(c, EPS, True)
        pts = [(float(p[0][0]) * k + CAP * GAP * 0.5, (h - float(p[0][1])) * k) for p in approx]
        if len(pts) < 4:
            continue
        is_hole = hierarchy[0][i][3] != -1
        sm = resample(pts, max(4.0, (y1 if False else 0) or 6.0))
        out.append((sm, is_hole))

    return out, w * k



def resample(pts, step):
    """按弧长均匀重采样，避免 approxPolyDP 带来的疏密不均"""
    n = len(pts)
    segs = []
    total = 0.0
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        segs.append((a, b, d))
        total += d
    if total <= 0:
        return pts
    count = max(8, int(total / step))
    out = []
    for k in range(count):
        t = total * k / count
        acc = 0.0
        for a, b, d in segs:
            if acc + d >= t:
                r = 0 if d == 0 else (t - acc) / d
                out.append((a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r))
                break
            acc += d
    return out

def area(pts):
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def main():
    crops = {}
    for cfg in CONFIG:
        p = os.path.join(SRC_DIR, cfg['path'])
        if not os.path.exists(p):
            print('missing', p)
            continue
        if cfg['cols']:
            im, m = mask_of(p)
            mid = m.shape[1] // 2
            left, right = m[:, :mid], m[:, mid:]
            left_rows, right_rows = cfg['rows']
            for tag, mm, rows in (('L', left, left_rows), ('R', right, right_rows)):
                tmp = os.path.join(os.path.dirname(p), '_tmp_%s_%s.png' % (cfg['path'], tag))
                cv2.imwrite(tmp, mm)
                n = harvest(tmp, rows, crops, cfg['path'] + ':' + tag)
                os.remove(tmp)
                print('  %-28s %-2s %d' % (cfg['path'], tag, n))
        else:
            n = harvest(p, cfg['rows'], crops, cfg['path'])
            print('  %-28s    %d' % (cfg['path'], n))

    print('\nchars:', len(crops))
    summary = {ch: len(v) for ch, v in sorted(crops.items())}
    print(json.dumps(summary, ensure_ascii=False))
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, 'glyph-sources.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    # 大写字高：从 H 的样本高度取中位数

    glyphs, order, advances = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    advances['.notdef'] = 500

    for ch, samples in sorted(crops.items()):
        # 优先用最高清的样本组，再在其中选“中位形状”，剔除切分错位
        top = max(h for h, _, _ in samples)
        samples = [x for x in samples if x[0] >= 0.92 * top]
        feats = []
        for h, cr, cp in samples:
            small = cv2.resize(cr, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
            feats.append(small.ravel())
        feats = np.array(feats)
        mean = feats.mean(axis=0)
        dist = np.abs(feats - mean).mean(axis=1)
        idx = int(np.argmin(dist))
        h_best, crop, cap_h = samples[idx]
        os.makedirs(os.path.join(OUT_DIR, 'chosen'), exist_ok=True)
        cv2.imwrite(os.path.join(OUT_DIR, 'chosen', '%s_%d.png' % (ch if ch.isalnum() else 'sym%02x' % ord(ch), h_best)), crop)
        contours, width = trace(crop, cap_h)
        if not contours:
            continue
        tpen = TTGlyphPen(None)
        for pts, is_hole in contours:
            a = area(pts)
            if is_hole and a < 0:
                pts = list(reversed(pts))
            elif (not is_hole) and a > 0:
                pts = list(reversed(pts))
            n = len(pts)
            if n < 4:
                continue
            mid = lambda u, v: ((u[0] + v[0]) / 2.0, (u[1] + v[1]) / 2.0)
            tpen.moveTo(mid(pts[-1], pts[0]))
            for i in range(n):
                tpen.qCurveTo(pts[i], mid(pts[i], pts[(i + 1) % n]))
            tpen.closePath()
        name = 'uni%04X' % ord(ch)
        try:
            glyphs[name] = tpen.glyph()
        except Exception as e:
            print('  skip', repr(ch), e)
            continue
        order.append(name)
        advances[name] = int(round(width + CAP * GAP))
        print('  %s  h=%dpx' % (ch, h_best))

    # 空格
    tpen = TTGlyphPen(None)
    glyphs['space'] = tpen.glyph()
    order.append('space')
    advances['space'] = int(CAP * 0.30)

    fb = FontBuilder(EM, isTTF=True)
    fb.setupGlyphOrder(order)
    cmap = {ord(ch): 'uni%04X' % ord(ch) for ch in crops if 'uni%04X' % ord(ch) in glyphs}
    cmap[0x20] = 'space'
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (advances[n], 0) for n in order})
    fb.setupHorizontalHeader(ascent=int(CAP * 1.2), descent=-int(CAP * 0.3))
    fb.setupNameTable({'familyName': 'HWLeica', 'styleName': 'Regular',
                       'uniqueFontIdentifier': 'HWLeica-Regular', 'fullName': 'HWLeica',
                       'psName': 'HWLeica-Regular', 'version': 'Version 2.0'})
    fb.setupOS2(sTypoAscender=int(CAP * 1.2), sTypoDescender=-int(CAP * 0.3),
                usWinAscent=int(CAP * 1.2), usWinDescent=int(CAP * 0.3))
    fb.setupPost()
    out = os.path.join(OUT_DIR, 'HWLeica-Regular.ttf')
    fb.save(out)
    print('\nsaved', out, os.path.getsize(out) // 1024, 'KB, glyphs', len(order) - 1)


if __name__ == '__main__':
    main()
