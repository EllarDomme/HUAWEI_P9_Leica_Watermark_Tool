#!/usr/bin/env python3
"""删除轮廓里的「尖刺点」——单个远低于基线的点。

P 的外轮廓里有一个 (4, -54) 的点，夹在两个 y>0 的点之间，
相当于沿左边缘扎下去又回来，形成一条极细的自我重叠，
小字号下抗锯齿会把它糊成一条淡影（看起来「外轮廓发白」）。

只删真正孤立的尖刺点，不整体平移，形状不受影响。
"""
import os
import sys

from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.recordingPen import DecomposingRecordingPen

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
]
DESC = set('gjpqy,;()[]{}|')
THRESHOLD = -6.0


def clean(font, name):
    glyf = font['glyf']
    g = glyf[name]
    coords, ends, flags = g.getCoordinates(glyf)
    pts = list(coords)
    fl = list(flags)

    kept_pts, kept_fl, new_ends = [], [], []
    start = 0
    removed = 0
    for end in ends:
        idxs = list(range(start, end + 1))
        n = len(idxs)
        for k, i in enumerate(idxs):
            y = pts[i][1]
            if y < THRESHOLD:
                prev_y = pts[idxs[(k - 1) % n]][1]
                next_y = pts[idxs[(k + 1) % n]][1]
                if prev_y > 0 and next_y > 0:
                    removed += 1
                    continue
            kept_pts.append(pts[i])
            kept_fl.append(fl[i])
        new_ends.append(len(kept_pts) - 1)
        start = end + 1

    if not removed:
        return 0

    gly = _build(kept_pts, kept_fl, new_ends)
    glyf[name] = gly
    return removed


def _build(pts, fl, ends):
    pen = TTGlyphPen(None)
    i = 0
    for e in ends:
        seg = list(range(i, e + 1))
        i = e + 1
        if not seg:
            continue
        # 以 on-curve 点开头；若全是曲线点，用第一个
        first_on = next((k for k in seg if fl[k] & 1), None)
        if first_on is None:
            first_on = seg[0]
        order = seg[first_on:] + seg[:first_on]
        pen.moveTo(pts[order[0]])
        k = 1
        while k < len(order):
            idx = order[k]
            if fl[idx] & 1:
                pen.lineTo(pts[idx])
                k += 1
            else:
                # 收集连续曲线点，直到遇到 on-curve 点（或绕回起点）
                ctrl = []
                while k < len(order) and not (fl[order[k]] & 1):
                    ctrl.append(pts[order[k]])
                    k += 1
                end_pt = pts[order[k]] if k < len(order) else pts[order[0]]
                pen.qCurveTo(*(ctrl + [end_pt]))
                k += 1
        pen.closePath()
    return pen.glyph()


def main():
    for path in FONTS:
        font = TTFont(path)
        cmap = font.getBestCmap()
        glyf = font['glyf']
        total = 0
        for cp, name in cmap.items():
            ch = chr(cp)
            if ch in DESC:
                continue
            g = glyf[name]
            if not hasattr(g, 'yMin') or g.yMin >= THRESHOLD:
                continue
            n = clean(font, name)
            if n:
                total += n
                print('  %s %s 删除尖刺点 %d 个' % (os.path.basename(path), ch, n))
        font.save(path)
        print(os.path.basename(path), '处理完成，共删', total)


if __name__ == '__main__':
    main()
