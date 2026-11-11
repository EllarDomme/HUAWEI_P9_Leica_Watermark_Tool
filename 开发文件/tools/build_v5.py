#!/usr/bin/env python3
"""用逐字符高清抠图重建 HWLeica。

每个字符一张 PNG，直接描轮廓（保角拟合），再按旧字体的度量对齐：
字高一致、基线一致、水平居中、字宽沿用旧值。
"""
import os
import sys

import cv2
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_full3 import CAP, EM

SRC = r"E:\DeskTop\字符抠图高清版\chars"
OLD = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
OUT = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"

SYMBOLS = {
    'backslash': '\\', 'colon': ':', 'dash': '-', 'dot': '.', 'doublequote': '"',
    'equal': '=', 'exclaim': '!', 'question': '?', 'singlequote': "'", 'slash': '/',
}


def load_old():
    f = TTFont(OLD)
    cmap = f.getBestCmap()
    info = {}
    for cp, name in cmap.items():
        ch = chr(cp)
        g = f['glyf'][name]
        if not hasattr(g, 'xMin'):
            continue
        adv = f['hmtx'][name][0]
        info[ch] = dict(x0=g.xMin, y0=g.yMin, x1=g.xMax, y1=g.yMax, adv=adv)
    return info


def load_mask(path):
    raw = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if raw is None:
        return None
    if raw.ndim == 3 and raw.shape[2] == 4:
        gray = raw[:, :, 3]          # 用 alpha 当遮罩，边缘最准
    else:
        g = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        gray = 255 - g if np.median(g) > 128 else g
    _, m = cv2.threshold(gray, 110, 255, cv2.THRESH_BINARY)
    n, lab, st, _ = cv2.connectedComponentsWithStats((m > 0).astype(np.uint8), 8)
    if n <= 1:
        return None
    areas = st[1:, 4]
    big = areas.max()
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] >= max(40, 0.03 * big):
            keep[lab == i] = 255
    ys, xs = np.where(keep > 0)
    if not len(xs):
        return None
    return keep[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def vectorize_poly(crop, target_h):
    h, w = crop.shape
    k = target_h / float(h)
    cs, hier = cv2.findContours(crop, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return [], 0.0
    out = []
    for i, c in enumerate(cs):
        if cv2.contourArea(c) < 5:
            continue
        ap = cv2.approxPolyDP(c, 0.9, True)
        if len(ap) < 3:
            continue
        pts = [(float(p[0][0]) * k, (h - float(p[0][1])) * k) for p in ap]
        is_hole = hier[0][i][3] != -1
        a = 0.0
        for j in range(len(pts)):
            x1, y1 = pts[j]
            x2, y2 = pts[(j + 1) % len(pts)]
            a += x1 * y2 - x2 * y1
        if (is_hole and a < 0) or ((not is_hole) and a > 0):
            pts.reverse()
        out.append((pts, is_hole))
    return out, w * k


def emit(cmds, dx, dy):
    out = []
    for cmd in cmds:
        pts = []
        for p in cmd[1:]:
            if isinstance(p, tuple) and len(p) == 2:
                pts.append((p[0] + dx, p[1] + dy))
            else:
                pts.append(p)
        out.append((cmd[0],) + tuple(pts))
    return out


def bbox_of(cmds):
    xs, ys = [], []
    for cmd in cmds:
        for p in cmd[1:]:
            if isinstance(p, tuple) and len(p) == 2:
                xs.append(p[0])
                ys.append(p[1])
    return min(xs), min(ys), max(xs), max(ys)


def main():
    old = load_old()
    files = []
    for sub in ('upper', 'lower', 'digit'):
        d = os.path.join(SRC, sub)
        if os.path.isdir(d):
            for n in sorted(os.listdir(d)):
                if n.endswith('.png'):
                    files.append((n[:-4], os.path.join(d, n)))
    d = os.path.join(SRC, 'symbol')
    if os.path.isdir(d):
        for n in sorted(os.listdir(d)):
            if n.endswith('.png'):
                ch = SYMBOLS.get(n[:-4])
                if ch:
                    files.append((ch, os.path.join(d, n)))

    print('files:', len(files))

    glyphs, order, adv = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    adv['.notdef'] = 500

    for ch, path in files:
        crop = load_mask(path)
        if crop is None or ch not in old:
            continue
        h, w = crop.shape
        ref = old[ch]
        target_h = ref['y1'] - ref['y0']

        polys, _ = vectorize_poly(crop, target_h)
        if not polys:
            print('  empty', ch)
            continue
        xs = [p[0] for pts, _ in polys for p in pts]
        ys = [p[1] for pts, _ in polys for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        ink_w = x1 - x0
        adv_w = max(ref['adv'], ink_w + CAP * 0.17)
        dx = adv_w / 2.0 - (x0 + x1) / 2.0
        dy = ref['y0'] - y0

        tpen = TTGlyphPen(None)
        for pts, is_hole in polys:
            tpen.moveTo((pts[0][0] + dx, pts[0][1] + dy))
            for p in pts[1:]:
                tpen.lineTo((p[0] + dx, p[1] + dy))
            tpen.closePath()

        name = 'uni%04X' % ord(ch)
        try:
            glyphs[name] = tpen.glyph()
        except Exception as e:
            print('  fail', ch, e)
            continue
        order.append(name)
        adv[name] = int(round(adv_w))

    tpen = TTGlyphPen(None)
    glyphs['space'] = tpen.glyph()
    order.append('space')
    adv['space'] = int(CAP * 0.30)

    chars = [ch for ch, _ in files if ch in old]
    fb = FontBuilder(EM, isTTF=True)
    fb.setupGlyphOrder(order)
    cmap = {ord(ch): 'uni%04X' % ord(ch) for ch in chars if 'uni%04X' % ord(ch) in glyphs}
    cmap[0x20] = 'space'
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (adv[n], 0) for n in order})
    fb.setupHorizontalHeader(ascent=int(CAP * 1.2), descent=-int(CAP * 0.3))
    fb.setupNameTable({'familyName': 'HWLeica', 'styleName': 'Regular',
                       'uniqueFontIdentifier': 'HWLeica-Regular', 'fullName': 'HWLeica',
                       'psName': 'HWLeica-Regular', 'version': 'Version 5.0'})
    fb.setupOS2(sTypoAscender=int(CAP * 1.2), sTypoDescender=-int(CAP * 0.3),
                usWinAscent=int(CAP * 1.2), usWinDescent=int(CAP * 0.3))
    fb.setupPost()
    fb.save(OUT)
    print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB, glyphs', len(order) - 1)


if __name__ == '__main__':
    main()
