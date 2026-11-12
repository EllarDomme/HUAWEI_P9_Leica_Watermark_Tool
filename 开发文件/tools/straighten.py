#!/usr/bin/env python3
"""把「应该是直边」的地方真正拉直。

描摹/内缩出来的轮廓，直边上会有一串几乎共线但略偏的点，
两笔相交的地方尤其明显：斜边与横边交界处会看到轻微弯曲（凹陷）。

这里做共线简化：若中间点相对前后两点连线的偏移小于 1.2 单位，
就把中间点删掉，让这一段变成真正的直线。
"""
import math
import os
import sys

from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Bold.ttf",
]
TOL = 1.2      # 允许的横向偏移（单位）
ONLY = None    # None = 所有字形；或写成 "X6" 只处理这些


def perp(a, b, p):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return 1e9
    return abs(dx * (ay - p[1]) - (ax - p[0]) * dy) / L


def straighten_contour(pts, flags):
    """pts/flags 按轮廓顺序；返回简化后的 (pts, flags)"""
    changed = True
    while changed and len(pts) > 4:
        changed = False
        n = len(pts)
        keep = [True] * n
        for i in range(n):
            if not (flags[i] & 1):
                continue
            j = (i - 1) % n
            k = (i + 1) % n
            if not (flags[j] & 1) or not (flags[k] & 1):
                continue
            if perp(pts[j], pts[k], pts[i]) < TOL:
                keep[i] = False
                changed = True
        if changed:
            pts = [p for p, q in zip(pts, keep) if q]
            flags = [f for f, q in zip(flags, keep) if q]
    return pts, flags


def rebuild(glyf, g, tol=TOL):
    coords, ends, flags = g.getCoordinates(glyf)
    out_pts, out_fl, new_ends = [], [], []
    start = 0
    for e in ends:
        seg_pts = [(coords[i][0], coords[i][1]) for i in range(start, e + 1)]
        seg_fl = [flags[i] for i in range(start, e + 1)]
        start = e + 1
        seg_pts, seg_fl = straighten_contour(seg_pts, seg_fl)
        if len(seg_pts) < 3:
            continue
        out_pts.extend(seg_pts)
        out_fl.extend(seg_fl)
        new_ends.append(len(out_pts) - 1)

    pen = TTGlyphPen(None)
    i = 0
    for e in new_ends:
        seg = list(range(i, e + 1))
        i = e + 1
        first_on = next((k for k in seg if out_fl[k] & 1), seg[0])
        order = seg[first_on:] + seg[:first_on]
        pen.moveTo(out_pts[order[0]])
        k = 1
        while k < len(order):
            idx = order[k]
            if out_fl[idx] & 1:
                pen.lineTo(out_pts[idx])
                k += 1
            else:
                ctrl = []
                while k < len(order) and not (out_fl[order[k]] & 1):
                    ctrl.append(out_pts[order[k]])
                    k += 1
                endp = out_pts[order[k]] if k < len(order) else out_pts[order[0]]
                pen.qCurveTo(*(ctrl + [endp]))
                k += 1
        pen.closePath()
    return pen.glyph()


def main():
    for fp in FONTS:
        font = TTFont(fp)
        cmap = font.getBestCmap()
        glyf = font['glyf']
        total = 0
        for cp, name in cmap.items():
            ch = chr(cp)
            if ONLY and ch not in ONLY:
                continue
            g = glyf[name]
            if not hasattr(g, 'numberOfContours') or g.numberOfContours <= 0:
                continue
            before = len(g.getCoordinates(glyf)[0])
            ng = rebuild(glyf, g)
            ng.recalcBounds(glyf)
            after = len(ng.getCoordinates(glyf)[0])
            if after < before:
                glyf[name] = ng
                total += before - after
        font.save(fp)
        print(os.path.basename(fp), '拉直后共减少点', total)


if __name__ == '__main__':
    main()
