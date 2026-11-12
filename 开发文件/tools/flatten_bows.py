#!/usr/bin/env python3
"""把「几乎就是直线、却带一点点弧度」的二次曲线改成直线。

描摹出来的边常常是 control 点偏离弦 1-2 单位的二次曲线，
放大看就是轻微的起伏或毛刺。改成直线后边就真正直了。
"""
import math
import os

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
]
TOL = 2.2        # control 点离弦多近就当作直线


def flatten(g, glyf, tol=TOL):
    co, ends, fl = g.getCoordinates(glyf)
    pts, fls, new_ends = [], [], []
    start = 0
    changed = 0
    for e in ends:
        idx = list(range(start, e + 1))
        start = e + 1
        n = len(idx)
        if n < 2:
            continue
        # 找第一个 on-curve 作为起点
        first = next((k for k in range(n) if fl[idx[k]] & 1), None)
        if first is None:
            continue
        order = idx[first:] + idx[:first]
        cur = [{'p': (co[order[0]][0], co[order[0]][1]), 'on': True}]
        k = 1
        while k < n:
            i = order[k]
            if fl[i] & 1:
                cur.append({'p': (co[i][0], co[i][1]), 'on': True})
                k += 1
            else:
                ctrl = []
                while k < n and not (fl[order[k]] & 1):
                    ctrl.append((co[order[k]][0], co[order[k]][1]))
                    k += 1
                endp = (co[order[k]][0], co[order[k]][1]) if k < n else cur[0]['p']
                if len(ctrl) == 1:
                    last = cur[-1]
                    a = last['p'] if 'p' in last else last['end']
                    c = ctrl[0]; b = endp
                    ax, ay = a; bx, by = b; cx, cy = c
                    dx, dy = bx - ax, by - ay
                    L = math.hypot(dx, dy) or 1e-6
                    d = abs(dx * (ay - cy) - (ax - cx) * dy) / L
                    if d < tol and L > 20:
                        cur.append({'p': b, 'on': True})
                        changed += 1
                        k += 1
                        continue
                cur.append({'q': ctrl, 'end': endp})
                k += 1

        if len(cur) < 3:
            continue
        for item in cur:
            if 'q' in item:
                for c in item['q']:
                    pts.append(c); fls.append(0)
                pts.append(item['end']); fls.append(1)
            else:
                pts.append(item['p']); fls.append(1)
        new_ends.append(len(pts) - 1)

    if not changed:
        return g, 0

    pen = TTGlyphPen(None)
    i = 0
    for e in new_ends:
        seg = list(range(i, e + 1))
        i = e + 1
        pen.moveTo(pts[seg[0]])
        k = 1
        while k < len(seg):
            j = seg[k]
            if fls[j] & 1:
                pen.lineTo(pts[j]); k += 1
            else:
                ctrl = []
                while k < len(seg) and not (fls[seg[k]] & 1):
                    ctrl.append(pts[seg[k]]); k += 1
                endp = pts[seg[k]] if k < len(seg) else pts[seg[0]]
                pen.qCurveTo(*(ctrl + [endp]))
                k += 1
        pen.closePath()
    return pen.glyph(), changed


def main():
    for fp in FONTS:
        if not os.path.exists(fp):
            continue
        font = TTFont(fp)
        cmap = font.getBestCmap()
        glyf = font['glyf']
        total = 0
        for cp, name in sorted(cmap.items()):
            g = glyf[name]
            if getattr(g, 'numberOfContours', 0) <= 0:
                continue
            ng, n = flatten(g, glyf)
            if n:
                ng.recalcBounds(glyf)
                glyf[name] = ng
                total += n
        font.save(fp)
        print(os.path.basename(fp), '拉直曲线', total, '段')


if __name__ == '__main__':
    main()
