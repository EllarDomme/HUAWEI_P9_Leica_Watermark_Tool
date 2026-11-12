#!/usr/bin/env python3
"""清理细体里的微小锯齿。

细体是「常规轮廓内缩」生成的，布尔运算在拐角处会留下一串
间距不到 3 单位的点，小字号渲染时就是毛刺。

这里把间距过近的点合并，并丢掉面积过小的碎片轮廓。
"""
import os
import sys

from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Bold.ttf",
]
MIN_DIST = 2.6        # 小于这个距离的点合并


def clean_glyph(glyf, g):
    coords, ends, flags = g.getCoordinates(glyf)
    out_pts, out_fl, new_ends = [], [], []
    start = 0
    dropped = 0
    for e in ends:
        idx = list(range(start, e + 1))
        start = e + 1
        kept = []
        for i in idx:
            p = coords[i]
            if kept:
                q = kept[-1][0]
                if ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 < MIN_DIST:
                    dropped += 1
                    continue
            kept.append((p, flags[i]))
        # 首尾过近也去掉
        if len(kept) > 1:
            p0, pk = kept[0][0], kept[-1][0]
            if ((p0[0] - pk[0]) ** 2 + (p0[1] - pk[1]) ** 2) ** 0.5 < MIN_DIST:
                kept.pop()
                dropped += 1
        if len(kept) < 3:
            continue
        for p, f in kept:
            out_pts.append(p)
            out_fl.append(f)
        new_ends.append(len(out_pts) - 1)

    if dropped == 0:
        return None

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
    return pen.glyph(), dropped


def main():
    for fp in FONTS:
        font = TTFont(fp)
        cmap = font.getBestCmap()
        glyf = font['glyf']
        total = 0
        for cp, name in cmap.items():
            g = glyf[name]
            if not hasattr(g, 'numberOfContours') or g.numberOfContours <= 0:
                continue
            res = clean_glyph(glyf, g)
            if not res:
                continue
            new, dropped = res
            new.recalcBounds(glyf)
            glyf[name] = new
            total += dropped
        font.save(fp)
        print(os.path.basename(fp), '合并微小点', total)


if __name__ == '__main__':
    main()
