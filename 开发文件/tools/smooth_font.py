#!/usr/bin/env python3
"""把多边形轮廓的字体平滑成真曲线。

做法：每条轮廓先 RDP 找拐角，拐角之间若偏离弦线 > 阈值，就拟合一条二次曲线，
否则保留直线。点数会大幅下降，边缘变顺。
"""
import os
import sys

import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

SRC = r"D:\P9徕卡水印工具\开发文件\fonts\RoundCustom-加宽8.ttf"
DST = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Smooth.ttf"

RDP_EPS = 5.0      # 拐角判定（units，em=1000）
FIT_TOL = 2.2      # 低于此偏差保持直线


def rdp(points, eps):
    n = len(points)
    if n < 3:
        return list(range(n))
    keep = [0, n - 1]
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a = np.array(points[i])
        b = np.array(points[j])
        ab = b - a
        norm = np.linalg.norm(ab) or 1e-6
        best, idx = 0.0, -1
        for k in range(i + 1, j):
            p = np.array(points[k])
            d = abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / norm
            if d > best:
                best, idx = d, k
        if best > eps and idx > 0:
            keep.append(idx)
            stack.append((i, idx))
            stack.append((idx, j))
    return sorted(set(keep))


def fit(span):
    a = np.array(span[0])
    b = np.array(span[-1])
    ab = b - a
    norm = np.linalg.norm(ab) or 1e-6
    dmax, pmax = 0.0, None
    for p in span[1:-1]:
        p = np.array(p)
        d = abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / norm
        if d > dmax:
            dmax, pmax = d, p
    if dmax <= FIT_TOL or pmax is None:
        return ('L', tuple(b))
    ctrl = 2.0 * pmax - (a + b) / 2.0
    return ('Q', tuple(ctrl), tuple(b))


def smooth_glyph(font, name):
    gs = font.getGlyphSet()
    rec = DecomposingRecordingPen(gs)
    gs[name].draw(rec)

    contours, cur = [], []
    for op, args in rec.value:
        if op == 'moveTo':
            if cur:
                contours.append(cur)
            cur = [args[0]]
        elif op == 'lineTo':
            cur.append(args[0])
        elif op == 'qCurveTo':
            # 输入本身就是折线，这里只兜底
            pts = list(args)
            if isinstance(pts[-1], tuple):
                cur.append(pts[-1])
        elif op == 'curveTo':
            c1, c2, end = args
            cur.append(end)
        elif op == 'closePath':
            if cur:
                contours.append(cur)
                cur = []
    if cur:
        contours.append(cur)

    pen = TTGlyphPen(None)
    total_pts = 0
    for pts in contours:
        pts = [tuple(map(float, p)) for p in pts]
        if len(pts) < 6:
            continue
        # 去掉重复点
        clean = [pts[0]]
        for p in pts[1:]:
            if abs(p[0] - clean[-1][0]) > 0.01 or abs(p[1] - clean[-1][1]) > 0.01:
                clean.append(p)
        pts = clean
        if len(pts) < 6:
            continue
        idx = rdp(pts, RDP_EPS)
        if len(idx) < 3:
            continue
        pen.moveTo(pts[idx[0]])
        total_pts += 1
        for a, b in zip(idx, idx[1:] + [idx[0] + len(pts)]):
            span = pts[a:b + 1] if b <= len(pts) else pts[a:] + pts[:b - len(pts) + 1]
            if len(span) < 2:
                continue
            cmd = fit(span)
            if cmd[0] == 'L':
                pen.lineTo(cmd[1])
                total_pts += 1
            else:
                pen.qCurveTo(cmd[1], cmd[2])
                total_pts += 2
        pen.closePath()
    return pen.glyph(), total_pts


def main():
    font = TTFont(SRC)
    glyf = font['glyf']
    before = after = 0
    for name in font.getGlyphOrder():
        if name == '.notdef':
            continue
        g = glyf[name]
        if not hasattr(g, 'numberOfContours') or g.numberOfContours <= 0:
            continue
        coords, ends, flags = g.getCoordinates(glyf)
        before += len(coords)
        new, pts = smooth_glyph(font, name)
        glyf[name] = new
        after += pts
    font.save(DST)
    print('points before', before, '-> after', after)
    print('saved', DST, os.path.getsize(DST) // 1024, 'KB')


if __name__ == '__main__':
    main()
