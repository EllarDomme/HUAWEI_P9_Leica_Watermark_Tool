#!/usr/bin/env python3
"""专业重绘细体 X：两条等宽对角线，端点竖直切平，交点干净。

做法：把两条中心线加粗（平头端帽），合并后与字框求交，
端点自然成为竖直切面；交点由布尔并集得到锐利的内角。
"""
import os

import pathops
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib import TTFont

SRC = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf"
W = 439.0
H = 700.0
T = 88.0           # 笔画宽度（细体，常规约 105，按 0.83 比例）


def bar(p0, p1, t, cap=pathops.LineCap.BUTT_CAP):
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo(p0)
    pen.lineTo(p1)
    p.stroke(t, cap, pathops.LineJoin.ROUND_JOIN, 4.0)
    p.convertConicsToQuads()
    return p


def box(w, h):
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo((0, 0))
    pen.lineTo((w, 0))
    pen.lineTo((w, h))
    pen.lineTo((0, h))
    pen.closePath()
    return p


def build():
    # 端点是圆头：圆心放在距角落 r 处，圆正好与字框相切
    r = T / 2
    a = bar((r, r), (W - r, H - r), T, pathops.LineCap.ROUND_CAP)
    b = bar((r, H - r), (W - r, r), T, pathops.LineCap.ROUND_CAP)
    u = pathops.op(a, b, pathops.PathOp.UNION, fix_winding=True)
    u.convertConicsToQuads()
    return u


def main():
    font = TTFont(SRC)
    cmap = font.getBestCmap()
    glyf = font['glyf']
    name = cmap[ord('X')]
    adv, lsb = font['hmtx'][name]

    p = build()
    tpen = TTGlyphPen(None)
    cu = Cu2QuPen(tpen, 0.8, reverse_direction=False)
    p.draw(cu)
    g = tpen.glyph()
    g.recalcBounds(glyf)
    glyf[name] = g
    font.save(SRC)
    print('X 重绘:', g.xMin, g.yMin, g.xMax, g.yMax, '| 点', len(g.getCoordinates(glyf)[0]))


if __name__ == '__main__':
    main()
