#!/usr/bin/env python3
"""把参考图里摘出的字形拼成字体（HWLeica）。

防锯齿三步：
1. 8 倍放大 + 高斯模糊后再二值化（把像素台阶抹平）
2. 轮廓多边形化后做 Chaikin 平滑（把折角修圆）
3. 用直线段建字形（TrueType 会自动抗锯齿渲染）
"""
import os
import sys
import glob

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

EM = 1000
CAP = 700
UP = 8
GAP = 0.13
SMOOTH_ITER = 1


def char_of(path):
    base = os.path.basename(path)
    ch = base.rsplit('_', 1)[0]
    if ch.startswith('sym'):
        ch = chr(int(ch[3:], 16))
    return ch


def signed_area(pts):
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def chaikin(pts, iters=SMOOTH_ITER):
    for _ in range(iters):
        out = []
        n = len(pts)
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % n]
            out.append((0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]))
            out.append((0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]))
        pts = out
    return pts


def cap_height_of(d):
    hs = []
    for ch in 'HELT':
        for p in glob.glob(os.path.join(d, ch + '_*.png')):
            hs.append(cv2.imread(p, 0).shape[0])
    return float(np.median(hs)) if hs else None


def trace(path, cap_px):
    im = cv2.imread(path, 0)
    big = cv2.resize(im, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), UP * 0.55)
    _, m = cv2.threshold(big, 128, 255, cv2.THRESH_BINARY)

    contours, hierarchy = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hierarchy is None:
        return [], 0.0

    k = CAP / (cap_px * UP)
    H = big.shape[0]
    out = []
    for i, c in enumerate(contours):
        if cv2.contourArea(c) < 40:
            continue
        approx = cv2.approxPolyDP(c, 1.4 * UP, True)
        pts = [(float(p[0][0]) * k, (H - float(p[0][1])) * k) for p in approx]
        if len(pts) < 4:
            continue
        pts = chaikin(pts)
        is_hole = hierarchy[0][i][3] != -1
        a = signed_area(pts)
        if is_hole and a < 0:
            pts.reverse()
        elif (not is_hole) and a > 0:
            pts.reverse()
        out.append(pts)

    return out, im.shape[1] * CAP / cap_px


def main():
    out = sys.argv[1]
    dirs = [d for d in sys.argv[2:] if os.path.isdir(d)]

    pool = {}
    for d in dirs:
        cap = cap_height_of(d)
        if not cap:
            print('  no cap height in', d)
            continue
        for p in glob.glob(os.path.join(d, '*.png')):
            pool.setdefault(char_of(p), []).append((p, cap))

    print('chars:', len(pool))
    glyphs, order, advances = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    advances['.notdef'] = 500

    for ch, samples in sorted(pool.items()):
        p, cap = max(samples, key=lambda s: cv2.imread(s[0], 0).shape[0])
        contours, width = trace(p, cap)
        if not contours:
            continue
        tpen = TTGlyphPen(None)
        for pts in contours:
            n = len(pts)
            if n < 4:
                continue
            mid = lambda a, b: ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
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

    fb = FontBuilder(EM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({ord(ch): 'uni%04X' % ord(ch) for ch in pool if 'uni%04X' % ord(ch) in glyphs})
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (advances[n], 0) for n in order})
    fb.setupHorizontalHeader(ascent=int(CAP * 1.2), descent=-int(CAP * 0.3))
    fb.setupNameTable({'familyName': 'HWLeica', 'styleName': 'Regular',
                       'uniqueFontIdentifier': 'HWLeica-Regular', 'fullName': 'HWLeica',
                       'psName': 'HWLeica-Regular', 'version': 'Version 1.2'})
    fb.setupOS2(sTypoAscender=int(CAP * 1.2), sTypoDescender=-int(CAP * 0.3),
                usWinAscent=int(CAP * 1.2), usWinDescent=int(CAP * 0.3))
    fb.setupPost()
    fb.save(out)
    print('saved', out, os.path.getsize(out) // 1024, 'KB, glyphs', len(order) - 1)


if __name__ == '__main__':
    main()
