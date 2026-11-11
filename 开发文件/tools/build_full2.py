#!/usr/bin/env python3
"""从完整字表图提取 A–Z / a–z / 0–9，标点沿用已有样本，生成 HWLeica。"""
import os
import sys
import glob

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_font import trace

EM, CAP, GAP = 1000, 700, 0.13
SRC = r"D:\P9徕卡水印工具\开发文件\reference\full-charset.png"
OLD = r"D:\P9徕卡水印工具\开发文件\fonts\chosen"
OUT_TTF = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"

BANDS = {
    'upper': "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    'lower': "abcdefghijklmnopqrstuvwxyz",
    'digit': "0123456789",
}


def cc_blocks(m, y0, y1, th_ratio=0.25, min_area=60):
    band = m[y0:y1 + 1]
    bh = y1 - y0 + 1
    n, lab, st, _ = cv2.connectedComponentsWithStats((band > 0).astype(np.uint8), 8)
    boxes = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < min_area or h < th_ratio * bh:
            continue
        boxes.append([x, x + w - 1])
    boxes.sort()
    merged = []
    for b in boxes:
        if merged and b[0] <= merged[-1][1] + 6:
            merged[-1][1] = max(merged[-1][1], b[1])
        else:
            merged.append(list(b))
    return merged


def find_rows(m):
    rows = (m > 0).sum(axis=1)
    act = rows > rows.max() * 0.02
    out, start, gap = [], None, 0
    for y, a in enumerate(act):
        if a:
            if start is None:
                start = y
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= 5:
                out.append((start, y - gap))
                start, gap = None, 0
    if start is not None:
        out.append((start, len(act) - 1))
    return [b for b in out if b[1] - b[0] > 40]


def split_merged(m, y0, y1, x0, x1):
    band = m[y0:y1 + 1]
    prof = (band[:, x0:x1 + 1] > 0).sum(axis=0)
    mid = x0 + len(prof) // 2
    lo = max(x0 + 4, mid - len(prof) // 3)
    hi = min(x1 - 4, mid + len(prof) // 3)
    cut = lo + int(np.argmin(prof[lo - x0:hi - x0 + 1])) if hi > lo else mid
    return [(x0, cut), (cut + 1, x1)]


def crop_of(m, y0, y1, x0, x1):
    cell = m[y0:y1 + 1, x0:x1 + 1]
    ys, xs = np.where(cell > 0)
    if not len(xs):
        return None, 0
    top = ys.min()
    return cell[top:ys.max() + 1, xs.min():xs.max() + 1], int(top)


def main():
    g = cv2.imread(SRC, cv2.IMREAD_GRAYSCALE)
    _, m = cv2.threshold(g, 200, 255, cv2.THRESH_BINARY)
    bands = find_rows(m)
    print('rows', bands)
    if len(bands) < 3:
        raise SystemExit('row detection failed')
    up, low, dig = bands[0], bands[1], bands[2]
    # 小写行有下伸部（g j p q y），把行带往下多留 40px
    low = (low[0], min(m.shape[0] - 1, low[1] + 40))

    crops = {}

    # 大写
    blocks = cc_blocks(m, up[0], up[1])
    print('upper blocks', len(blocks))
    if len(blocks) == 26:
        for ch, (x0, x1) in zip(BANDS['upper'], blocks):
            c, top = crop_of(m, up[0], up[1], x0, x1)
            if c is not None:
                crops[ch] = (c, c.shape[0])          # 基线 = 底部

    # 小写（可能有一对粘连）
    blocks = cc_blocks(m, low[0], low[1])
    print('lower blocks', len(blocks))
    if len(blocks) == 25:
        # 这张图里 i 和 j 粘在一起（第 8 块），单独劈开
        i = 8
        a, b = split_merged(m, low[0], low[1], blocks[i][0], blocks[i][1])
        blocks = blocks[:i] + [list(a), list(b)] + blocks[i + 1:]
    if len(blocks) == 26:
        tmp = {}
        for ch, (x0, x1) in zip(BANDS['lower'], blocks):
            c, top = crop_of(m, low[0], low[1], x0, x1)
            if c is not None:
                tmp[ch] = (c, top)
        if 'o' in tmp:
            base_global = low[0] + tmp['o'][1] + tmp['o'][0].shape[0]
            for ch, (c, top) in tmp.items():
                crops[ch] = (c, base_global - (low[0] + top))
        else:
            for ch, (c, top) in tmp.items():
                crops[ch] = (c, c.shape[0])

    # 数字（行首到符号前）
    db = cc_blocks(m, dig[0], dig[1])
    print('digit+sym blocks', len(db))
    digits = db[:10] if len(db) >= 10 else []
    if len(digits) == 10:
        for ch, (x0, x1) in zip(BANDS['digit'], digits):
            c, top = crop_of(m, dig[0], dig[1], x0, x1)
            if c is not None:
                crops[ch] = (c, c.shape[0])

    # 标点沿用旧样本
    for p in glob.glob(os.path.join(OLD, 'sym*.png')):
        ch = chr(int(os.path.basename(p)[3:5], 16))
        img = cv2.imread(p, 0)
        if ch not in crops and img is not None:
            crops[ch] = (img, img.shape[0])
    for ch in "+|":
        p = os.path.join(OLD, 'sym%02x' % ord(ch) + '_34.png')
        if ch not in crops and os.path.exists(p):
            im2 = cv2.imread(p, 0)
            crops[ch] = (im2, im2.shape[0])

    print('chars:', len(crops), ''.join(sorted(crops)))

    cap_px = float(np.median([crops['A'][0].shape[0], crops['H'][0].shape[0], crops['E'][0].shape[0]]))
    print('cap px', cap_px)

    glyphs, order, adv = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    adv['.notdef'] = 500

    for ch in sorted(crops):
        crop, baseline = crops[ch]
        contours, width = trace(crop, cap_px, baseline)
        if not contours:
            print('  empty', repr(ch))
            continue
        tpen = TTGlyphPen(None)
        for pts, is_hole in contours:
            n = len(pts)
            if n < 4:
                continue
            mid = lambda u, v: ((u[0] + v[0]) / 2.0, (u[1] + v[1]) / 2.0)
            tpen.moveTo(mid(pts[-1], pts[0]))
            for i in range(n):
                tpen.qCurveTo(pts[i], mid(pts[i], pts[(i + 1) % n]))
            tpen.closePath()
        name = 'uni%04X' % ord(ch)
        glyphs[name] = tpen.glyph()
        order.append(name)
        adv[name] = int(round(width + CAP * GAP))

    tpen = TTGlyphPen(None)
    glyphs['space'] = tpen.glyph()
    order.append('space')
    adv['space'] = int(CAP * 0.30)

    fb = FontBuilder(EM, isTTF=True)
    fb.setupGlyphOrder(order)
    cmap = {ord(ch): 'uni%04X' % ord(ch) for ch in crops if 'uni%04X' % ord(ch) in glyphs}
    cmap[0x20] = 'space'
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (adv[n], 0) for n in order})
    fb.setupHorizontalHeader(ascent=int(CAP * 1.2), descent=-int(CAP * 0.3))
    fb.setupNameTable({'familyName': 'HWLeica', 'styleName': 'Regular',
                       'uniqueFontIdentifier': 'HWLeica-Regular', 'fullName': 'HWLeica',
                       'psName': 'HWLeica-Regular', 'version': 'Version 3.1'})
    fb.setupOS2(sTypoAscender=int(CAP * 1.2), sTypoDescender=-int(CAP * 0.3),
                usWinAscent=int(CAP * 1.2), usWinDescent=int(CAP * 0.3))
    fb.setupPost()
    fb.save(OUT_TTF)
    print('saved', OUT_TTF, os.path.getsize(OUT_TTF) // 1024, 'KB, glyphs', len(order) - 1)


if __name__ == '__main__':
    main()
