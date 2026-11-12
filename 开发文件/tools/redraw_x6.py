#!/usr/bin/env python3
"""单字重绘细体的 X 和 6（用构造法，不用内缩）。

X：两条对角线，端点按字框竖直切平。
6：一个圆环 + 一条上扬的笔画。
"""
import math
import os

import pathops
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib import TTFont

SRC = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf"
CAP = 700.0
STROKE = 104.0


def line(pts, w, cap=pathops.LineCap.BUTT_CAP):
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo(pts[0])
    for q in pts[1:]:
        pen.lineTo(q)
    p.stroke(w, cap, pathops.LineJoin.ROUND_JOIN, 4.0)
    p.convertConicsToQuads()
    return p


def poly(pts):
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo(pts[0])
    for q in pts[1:]:
        pen.lineTo(q)
    pen.closePath()
    return p


def circle(cx, cy, r):
    p = pathops.Path()
    pen = p.getPen()
    k = 0.5523 * r
    pen.moveTo((cx + r, cy))
    pen.curveTo((cx + r, cy + k), (cx + k, cy + r), (cx, cy + r))
    pen.curveTo((cx - k, cy + r), (cx - r, cy + k), (cx - r, cy))
    pen.curveTo((cx - r, cy - k), (cx - k, cy - r), (cx, cy - r))
    pen.curveTo((cx + k, cy - r), (cx + r, cy - k), (cx + r, cy))
    pen.closePath()
    p.convertConicsToQuads()
    return p


def build_X(W=415, H=700, t=STROKE):
    d = t * 1.42          # 对角线尽量在端点留出直角切面
    a = line([(d / 2, 0), (W - d / 2, H)], t)
    b = line([(W - d / 2, 0), (d / 2, H)], t)
    u = pathops.op(a, b, pathops.PathOp.UNION, fix_winding=True)
    u.convertConicsToQuads()
    return u


def build_6(W=410, H=700, t=STROKE):
    R = W / 2.0                       # 外圆半径
    cy = R                            # 底边贴基线
    cx = R
    outer = circle(cx, cy, R)
    inner = circle(cx, cy, R - t)
    ring = pathops.op(outer, inner, pathops.PathOp.DIFFERENCE, fix_winding=True)

    # 上扬笔画：从圆环左上，斜到右上角
    ang = math.radians(140)
    sx = cx + (R - t / 2) * math.cos(ang)
    sy = cy + (R - t / 2) * math.sin(ang)
    tail = line([(sx, sy), (W - t * 0.55, H - t * 0.5)], t, pathops.LineCap.ROUND_CAP)

    u = pathops.op(ring, tail, pathops.PathOp.UNION, fix_winding=True)
    u.convertConicsToQuads()
    return u


def apply(font, name, path):
    glyf = font['glyf']
    tpen = TTGlyphPen(None)
    cu = Cu2QuPen(tpen, 0.8, reverse_direction=False)
    path.draw(cu)
    g = tpen.glyph()
    g.recalcBounds(glyf)
    glyf[name] = g
    return g


def main():
    font = TTFont(SRC)
    cmap = font.getBestCmap()
    for ch, builder in (('X', build_X), ('6', build_6)):
        g = apply(font, cmap[ord(ch)], builder())
        print(ch, '重绘:', g.xMin, g.yMin, g.xMax, g.yMax)
    font.save(SRC)
    print('saved', os.path.getsize(SRC) // 1024, 'KB')


if __name__ == '__main__':
    main()
