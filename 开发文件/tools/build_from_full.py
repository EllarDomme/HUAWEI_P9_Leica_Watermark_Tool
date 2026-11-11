#!/usr/bin/env python3
"""从完整字表图（均匀排布）切出全部字形，并生成 HWLeica 字体。

这张图字母之间间距接近等距，所以用「等分 + 边界对齐到空白最小列」的方式切分。
"""
import os
import sys

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_font import trace

EM, CAP, GAP = 1000, 700, 0.13
SRC = r"D:\P9徕卡水印工具\开发文件\reference\full-charset.png"
OUT_TTF = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
OUT_CROPS = r"D:\P9徕卡水印工具\开发文件\fonts\chosen"

ROWS = [
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789?!/.:-\\'\"=",
]


def bands_of(m, th_ratio=0.02, min_gap=5):
    rows = (m > 0).sum(axis=1)
    act = rows > rows.max() * th_ratio
    out, start, gap = [], None, 0
    for y, a in enumerate(act):
        if a:
            if start is None:
                start = y
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= min_gap:
                out.append((start, y - gap))
                start, gap = None, 0
    if start is not None:
        out.append((start, len(act) - 1))
    return [b for b in out if b[1] - b[0] > 40]


def split_row(m, y0, y1, n, x_limit=None):
    band = m[y0:y1 + 1]
    prof = (band > 0).sum(axis=0)
    if x_limit:
        prof = prof.copy()
        prof[x_limit:] = 0
    ink = np.where(prof > 0)[0]
    if not len(ink):
        return []
    left, right = int(ink.min()), int(ink.max())
    step = (right - left) / float(n)
    bounds = [left]
    for i in range(1, n):
        target = int(round(left + i * step))
        lo = max(left + 2, int(target - step * 0.38))
        hi = min(right - 2, int(target + step * 0.38))
        if hi <= lo:
            bounds.append(target)
            continue
        seg = prof[lo:hi + 1]
        bounds.append(lo + int(np.argmin(seg)))
    bounds.append(right + 1)
    cells = []
    for i in range(n):
        x0, x1 = bounds[i], bounds[i + 1] - 1
        # 细字母（如 l）容易被切窄，向两侧各扩 30% 再重新裁
        if (x1 - x0 + 1) < 0.3 * step:
            pad = int(step * 0.3)
            x0 = max(0, x0 - pad)
            x1 = min(prof.shape[0] - 1, x1 + pad)
        cell = band[:, x0:x1 + 1]
        ys, xs = np.where(cell > 0)
        if not len(xs):
            continue
        cell = cell[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        cells.append(cell)
    return cells


def main():
    g = cv2.imread(SRC, cv2.IMREAD_GRAYSCALE)
    _, m = cv2.threshold(g, 170, 255, cv2.THRESH_BINARY)
    bands = bands_of(m)
    print('rows:', [(b[0], b[1]) for b in bands])
    if len(bands) != len(ROWS):
        print('!! row count mismatch')
        return

    os.makedirs(OUT_CROPS, exist_ok=True)
    crops = {}
    for (y0, y1), text in zip(bands, ROWS):
        cells = split_row(m, y0, y1, len(text), x_limit=m.shape[1] - 380 if text[0] == '0' else None)
        print('row %d: cells %d / chars %d' % (y0, len(cells), len(text)))
        if len(cells) != len(text):
            continue
        for ch, cell in zip(text, cells):
            crops.setdefault(ch, []).append(cell)

    print('chars:', len(crops))

    # 大写字高
    cap_px = float(np.median([c.shape[0] for c in crops['A']])) if 'A' in crops else 150.0
    print('cap px', cap_px)

    glyphs, order, adv = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    adv['.notdef'] = 500

    for ch in sorted(crops):
        crop = max(crops[ch], key=lambda c: c.shape[0] * c.shape[1])
        cv2.imwrite(os.path.join(OUT_CROPS, '%s_%d.png' % (ch if ch.isalnum() else 'sym%02x' % ord(ch), crop.shape[0])), crop)
        contours, width = trace(crop, cap_px)
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
                       'psName': 'HWLeica-Regular', 'version': 'Version 3.0'})
    fb.setupOS2(sTypoAscender=int(CAP * 1.2), sTypoDescender=-int(CAP * 0.3),
                usWinAscent=int(CAP * 1.2), usWinDescent=int(CAP * 0.3))
    fb.setupPost()
    fb.save(OUT_TTF)
    print('saved', OUT_TTF, os.path.getsize(OUT_TTF) // 1024, 'KB, glyphs', len(order) - 1)


if __name__ == '__main__':
    main()
