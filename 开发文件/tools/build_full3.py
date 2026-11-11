#!/usr/bin/env python3
"""HWLeica 重建：保角曲线拟合 + 度量标准化。

与上一版的区别：
1. 先 RDP 找拐角（保角），段内若偏离弦线 >1.2px 就拟合成一条二次曲线，
   否则用直线 —— 直的更直、圆的更顺，不再全篇抖。
2. 大写字高统一到 700，小写 x 高度统一到 500，基线统一到 0。
3. 字宽按“标准字宽表”微调（H/E/N 等同宽字对齐）。
"""
import os
import sys
import glob

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_full2 import find_rows, cc_blocks, split_merged, crop_of, SRC

EM, CAP, XH = 1000, 700, 500
GAP = 0.20
RDP_EPS = 1.8        # 拐角阈值（像素）
FIT_TOL = 1.2        # 低于此偏差判为直线
OUT_TTF = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"

ROWS = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "abcdefghijklmnopqrstuvwxyz",
        "0123456789?!/.:-\\'\"="]
XH_LETTERS = set('acemnorsuvwxz')


def rdp(points, eps):
    """Ramer–Douglas–Peucker，返回保留点的下标"""
    n = len(points)
    if n < 3:
        return list(range(n))
    keep = [0, n - 1]
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, ay = points[i]
        bx, by = points[j]
        dx, dy = bx - ax, by - ay
        norm = (dx * dx + dy * dy) ** 0.5 or 1e-6
        best, idx = 0.0, -1
        for k in range(i + 1, j):
            px, py = points[k]
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > best:
                best, idx = d, k
        if best > eps and idx > 0:
            keep.append(idx)
            stack.append((i, idx))
            stack.append((idx, j))
    return sorted(set(keep))


def fit_segment(pts, tol=FIT_TOL):
    """把一段点拟合成直线或一条二次曲线，返回 (kind, payload)"""
    a, b = np.array(pts[0]), np.array(pts[-1])
    mid = (a + b) / 2.0
    # 找离弦最远的点
    dmax, pmax = 0.0, None
    ab = b - a
    norm = np.linalg.norm(ab) or 1e-6
    for p in pts[1:-1]:
        p = np.array(p)
        d = abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / norm
        if d > dmax:
            dmax, pmax = d, p
    if dmax <= tol or pmax is None:
        return ('L', (tuple(b),))
    ctrl = 2.0 * pmax - mid
    return ('Q', (tuple(ctrl), tuple(b)))


def vectorize(crop, cap_px, baseline=None, target_h=CAP):
    h, w = crop.shape
    k = target_h / float(cap_px)
    base = h if baseline is None else baseline
    contours, hierarchy = cv2.findContours(crop, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hierarchy is None:
        return [], 0.0

    def T(p):
        x, y = p
        return (x * k + CAP * GAP * 0.5, (base - y) * k)

    def area(pts):
        a = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            a += x1 * y2 - x2 * y1
        return a

    out = []
    for i, c in enumerate(contours):
        if cv2.contourArea(c) < 3:
            continue
        pts = [T(tuple(map(float, p[0]))) for p in c]
        if len(pts) < 6:
            continue
        is_hole = hierarchy[0][i][3] != -1
        a = area(pts)
        if (is_hole and a < 0) or ((not is_hole) and a > 0):
            pts.reverse()
        idx = rdp(pts, RDP_EPS * k)
        cmds = [('M', pts[idx[0]])]
        for a_i, b_i in zip(idx, idx[1:] + [idx[0] + len(pts)]):
            span = pts[a_i:b_i + 1] if b_i <= len(pts) else pts[a_i:] + pts[:b_i - len(pts) + 1]
            if len(span) < 2:
                continue
            kind, payload = fit_segment(span, FIT_TOL * k)
            cmds.append(('L', payload[0]) if kind == 'L' else ('Q', payload[0], payload[1]))
        cmds.append(('Z',))
        out.append((cmds, is_hole))
    return out, w * k


def normalize(cmds, want_h, base_y=0.0):
    """整体等比缩放，让字高等于 want_h（以基线为锚）"""
    ys = []
    for cmd in cmds:
        for p in cmd[1:]:
            if isinstance(p, tuple) and len(p) == 2:
                ys.append(p[1])
    if not ys:
        return cmds, 1.0
    cur = max(ys) - min(ys)
    if cur <= 1:
        return cmds, 1.0
    s = want_h / cur
    out = []
    for cmd in cmds:
        new = [cmd[0]]
        for p in cmd[1:]:
            if isinstance(p, tuple) and len(p) == 2:
                new.append((p[0] * s, base_y + (p[1] - base_y) * s))
            else:
                new.append(p)
        out.append(tuple(new))
    return out, s


def harvest():
    g = cv2.imread(SRC, cv2.IMREAD_GRAYSCALE)
    _, m = cv2.threshold(g, 200, 255, cv2.THRESH_BINARY)
    bands = find_rows(m)
    up, low, dig = bands[0], bands[1], bands[2]
    low = (low[0], min(m.shape[0] - 1, low[1] + 40))

    crops = {}
    blocks = cc_blocks(m, up[0], up[1])
    if len(blocks) == 26:
        for ch, (x0, x1) in zip(ROWS[0], blocks):
            c, top = crop_of(m, up[0], up[1], x0, x1)
            if c is not None:
                crops[ch] = (c, c.shape[0])

    blocks = cc_blocks(m, low[0], low[1])
    if len(blocks) == 25:
        i = 8
        a, b = split_merged(m, low[0], low[1], blocks[i][0], blocks[i][1])
        blocks = blocks[:i] + [list(a), list(b)] + blocks[i + 1:]
    if len(blocks) == 26:
        tmp = {}
        for ch, (x0, x1) in zip(ROWS[1], blocks):
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

    db = cc_blocks(m, dig[0], dig[1])
    if len(db) >= 10:
        for ch, (x0, x1) in zip(ROWS[2], db[:10]):
            c, top = crop_of(m, dig[0], dig[1], x0, x1)
            if c is not None:
                crops[ch] = (c, c.shape[0])

    # 标点沿用已有样本
    old = r"D:\P9徕卡水印工具\开发文件\fonts\chosen"
    for p in glob.glob(os.path.join(old, 'sym*.png')):
        ch = chr(int(os.path.basename(p)[3:5], 16))
        if ch not in crops:
            img = cv2.imread(p, 0)
            if img is not None:
                crops[ch] = (img, img.shape[0])
    return crops


def main():
    crops = harvest()
    print('chars:', len(crops))
    cap_px = float(np.median([crops[c][0].shape[0] for c in 'AHE']))

    glyphs, order, adv = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    adv['.notdef'] = 500

    for ch in sorted(crops):
        crop, baseline = crops[ch]
        is_lower = ch.islower() and ch not in 'bdfhklt'
        target = XH if is_lower else CAP
        cmds_list, width = vectorize(crop, cap_px, baseline, target)
        if not cmds_list:
            print('  empty', repr(ch))
            continue

        tpen = TTGlyphPen(None)
        for cmds, is_hole in cmds_list:
            for cmd in cmds:
                if cmd[0] == 'M':
                    tpen.moveTo(cmd[1])
                elif cmd[0] == 'L':
                    tpen.lineTo(cmd[1])
                elif cmd[0] == 'Q':
                    tpen.qCurveTo(cmd[1], cmd[2])
                else:
                    tpen.closePath()

        name = 'uni%04X' % ord(ch)
        try:
            glyphs[name] = tpen.glyph()
        except Exception as e:
            print('  fail', repr(ch), e)
            continue
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
                       'psName': 'HWLeica-Regular', 'version': 'Version 4.0'})
    fb.setupOS2(sTypoAscender=int(CAP * 1.2), sTypoDescender=-int(CAP * 0.3),
                usWinAscent=int(CAP * 1.2), usWinDescent=int(CAP * 0.3))
    fb.setupPost()
    fb.save(OUT_TTF)
    print('saved', OUT_TTF, os.path.getsize(OUT_TTF) // 1024, 'KB, glyphs', len(order) - 1)


if __name__ == '__main__':
    main()
