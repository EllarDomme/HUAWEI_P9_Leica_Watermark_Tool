#!/usr/bin/env python3
"""先把大写字母顶/底部的孤立尖点去掉，再把高度统一到 700。

有些字母（M、V、Y）轮廓里有个别离群的尖点，比字身高出 30-50 单位。
它会把外框撑大，导致后面按外框归一化时把真正的字身缩小——
看起来就是「M、V、Y 比别的字矮」。
"""
import os

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Bold.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Bold.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Bold.ttf",
]
CAP = 700.0
ROUND = set('OCSGQ')
UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
GAP = 25      # 与次高层的落差超过这个值，就认为是离群尖点


def drop_spikes(glyf, g):
    co, ends, fl = g.getCoordinates(glyf)
    ys = [p[1] for p in co]
    if len(ys) < 6:
        return g, 0
    top = max(ys)
    second = max([y for y in ys if y < top - 1] or [top])
    bot = min(ys)
    secondb = min([y for y in ys if y > bot + 1] or [bot])
    drop_top = (top - second) > GAP
    drop_bot = (secondb - bot) > GAP
    if not (drop_top or drop_bot):
        return g, 0

    keep_pts, keep_fl, new_ends = [], [], []
    start = 0
    removed = 0
    for e in ends:
        idx = list(range(start, e + 1))
        start = e + 1
        kept = []
        for i in idx:
            y = co[i][1]
            if drop_top and y > second + 1:
                removed += 1
                continue
            if drop_bot and y < secondb - 1:
                removed += 1
                continue
            kept.append(i)
        if len(kept) < 3:
            continue
        for i in kept:
            keep_pts.append((co[i][0], co[i][1]))
            keep_fl.append(fl[i])
        new_ends.append(len(keep_pts) - 1)

    if removed == 0:
        return g, 0

    pen = TTGlyphPen(None)
    i = 0
    for e in new_ends:
        seg = list(range(i, e + 1))
        i = e + 1
        first_on = next((k for k in seg if keep_fl[k] & 1), seg[0])
        order = seg[first_on:] + seg[:first_on]
        pen.moveTo(keep_pts[order[0]])
        k = 1
        while k < len(order):
            idx = order[k]
            if keep_fl[idx] & 1:
                pen.lineTo(keep_pts[idx])
                k += 1
            else:
                ctrl = []
                while k < len(order) and not (keep_fl[order[k]] & 1):
                    ctrl.append(keep_pts[order[k]])
                    k += 1
                endp = keep_pts[order[k]] if k < len(order) else keep_pts[order[0]]
                pen.qCurveTo(*(ctrl + [endp]))
                k += 1
        pen.closePath()
    return pen.glyph(), removed


def main():
    for fp in FONTS:
        if not os.path.exists(fp):
            continue
        font = TTFont(fp)
        cmap = font.getBestCmap()
        glyf = font['glyf']
        spikes = 0
        fixed = 0
        for ch in UPPER:
            if ord(ch) not in cmap:
                continue
            g = glyf[cmap[ord(ch)]]
            if getattr(g, 'numberOfContours', 0) <= 0:
                continue
            g, n = drop_spikes(glyf, g)
            if n:
                spikes += n
            g.recalcBounds(glyf)
            h = g.yMax - g.yMin
            want = CAP + (4.0 if ch in ROUND else 0.0)
            if h > 0 and abs(h - want) > 1.5:
                s = want / h
                g.coordinates.scale((s, s))
                g.recalcBounds(glyf)
                fixed += 1
            dy = -g.yMin
            if abs(dy) > 0.01:
                g.coordinates.translate((0, dy))
                g.recalcBounds(glyf)
            glyf[cmap[ord(ch)]] = g
        font.save(fp)
        print(os.path.basename(fp), '去尖点', spikes, '归一', fixed)


if __name__ == '__main__':
    main()
