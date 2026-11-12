#!/usr/bin/env python3
"""按几何重画常规体的 A、W、X。

所有笔画等宽、圆头，交点用并集，所以边上不会有描摹残留的碎点。
尺寸由原字形量得（见 scan 结果）。
"""
import inspect
import os
import sys

import pathops
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib import TTFont

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
]


def stroke(p0, p1, w, cap=pathops.LineCap.ROUND_CAP):
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo(p0)
    pen.lineTo(p1)
    p.stroke(w, cap, pathops.LineJoin.ROUND_JOIN, 3.0)
    p.convertConicsToQuads()
    return p


def union(*ps):
    out = ps[0]
    for p in ps[1:]:
        out = pathops.op(out, p, pathops.PathOp.UNION, fix_winding=True)
        out.convertConicsToQuads()
    return out


def build_A(W=450, H=700, S=90):
    half = S / 2
    top = H - half - 4
    apex_x = W * 0.50
    left = stroke((half + 2, half), (apex_x, top), S)
    right = stroke((W - half - 2, half), (apex_x, top), S)
    # 横杠：从顶部算 0.70H，两端接在两条腿的中线上
    bar_y = H * 0.30
    t = (bar_y - half) / (top - half)
    cx_l = half + 2 + t * (apex_x - half - 2)
    cx_r = W - half - 2 + t * (apex_x - (W - half - 2))
    bar = stroke((cx_l, bar_y), (cx_r, bar_y), S, pathops.LineCap.BUTT_CAP)
    return union(left, right, bar)


def build_W(W=602, H=700, S=102):
    half = S / 2
    top = H - half - 2
    bot = half + 2
    # 两侧是竖直笔画，中间一个 V
    left_stem = stroke((half, bot), (half, top), S)
    right_stem = stroke((W - half, bot), (W - half, top), S)
    mid_x = W * 0.50
    v_left = stroke((half, bot), (mid_x, top), S)
    v_right = stroke((mid_x, top), (W - half, bot), S)
    return union(left_stem, right_stem, v_left, v_right)


def build_X(W=438, H=700, S=100):
    half = S / 2
    top = H - half
    bot = half
    a = stroke((half, bot), (W - half, top), S)
    b = stroke((W - half, bot), (half, top), S)
    return union(a, b)


BUILDERS = {'A': build_A, 'W': build_W, 'X': build_X}


def apply(fp, k=1.0):
    font = TTFont(fp)
    cmap = font.getBestCmap()
    glyf = font['glyf']
    for ch, fn in BUILDERS.items():
        if ord(ch) not in cmap:
            continue
        name = cmap[ord(ch)]
        g0 = glyf[name]
        g0.recalcBounds(glyf)
        x0, y0 = float(g0.xMin), float(g0.yMin)
        Wd = round(float(g0.xMax - g0.xMin))
        Ht = round(float(g0.yMax - g0.yMin))

        kw = {'W': Wd, 'H': Ht}
        sig = inspect.signature(fn)
        if 'S' in sig.parameters:
            kw['S'] = round(sig.parameters['S'].default * k)
        p = fn(**kw)

        tp = TTGlyphPen(None)
        cu = Cu2QuPen(tp, 0.8, reverse_direction=False)
        p.draw(cu)
        g = tp.glyph()
        g.recalcBounds(glyf)
        g.coordinates.translate((x0 - g.xMin, y0 - g.yMin))
        g.recalcBounds(glyf)
        glyf[name] = g
        print(' ', ch, end='', flush=True)
    font.save(fp)
    print('\n已重画 A/W/X:', os.path.basename(fp))


if __name__ == '__main__':
    k = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    for f in FONTS:
        apply(f, k)
