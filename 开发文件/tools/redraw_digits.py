#!/usr/bin/env python3
"""按构造重画常规体的 0、4、6。

用等宽笔画 + 圆角/圆头拼出来，边缘是干净的几何线，不再有描摹留下的
细缝和毛刺。尺寸与原来的字形对齐（宽、高、基线）。
"""
import os

import pathops
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib import TTFont

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
]
K = 0.5523


def rrect(x0, y0, x1, y1, r):
    p = pathops.Path()
    pen = p.getPen()
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    pen.moveTo((x0 + r, y0))
    pen.lineTo((x1 - r, y0))
    pen.curveTo((x1 - r + K * r, y0), (x1, y0 + r - K * r), (x1, y0 + r))
    pen.lineTo((x1, y1 - r))
    pen.curveTo((x1, y1 - r + K * r), (x1 - r + K * r, y1), (x1 - r, y1))
    pen.lineTo((x0 + r, y1))
    pen.curveTo((x0 + r - K * r, y1), (x0, y1 - r + K * r), (x0, y1 - r))
    pen.lineTo((x0, y0 + r))
    pen.curveTo((x0, y0 + r - K * r), (x0 + r - K * r, y0), (x0 + r, y0))
    pen.closePath()
    p.convertConicsToQuads()
    return p


def stroke(p0, p1, w):
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo(p0)
    pen.lineTo(p1)
    p.stroke(w, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 2.0)
    p.convertConicsToQuads()
    return p


def union(*paths):
    out = paths[0]
    for p in paths[1:]:
        out = pathops.op(out, p, pathops.PathOp.UNION, fix_winding=True)
        out.convertConicsToQuads()
    return out


def diff(a, b):
    out = pathops.op(a, b, pathops.PathOp.DIFFERENCE, fix_winding=True)
    out.convertConicsToQuads()
    return out


def build_zero(W=439, H=704, S=96, r=86):
    outer = rrect(0, 0, W, H, r)
    inner = rrect(S, S, W - S, H - S, r * 0.42)
    return diff(outer, inner)


def build_four(W=423, H=700, S=86):
    # 左竖：从顶部到底部横杠
    a = stroke((S / 2, H - S / 2), (S / 2, H * 0.315), S)
    # 横杠
    b = stroke((S / 2, H * 0.315), (W - S / 2, H * 0.315), S)
    # 右竖：从横杠上方一点，到基线
    c = stroke((W * 0.62, H * 0.44), (W * 0.62, S / 2), S)
    return union(a, b, c)


def build_six(W=489, H=700, S=91):
    bh = H * 0.615
    outer = rrect(0, 0, W, bh, 78)
    inner = rrect(S + 8, S + 6, W - S - 8, bh - S - 6, 52)
    bowl = diff(outer, inner)
    # 斜尾：从碗左上回到字顶
    tail = stroke((S * 0.55, bh - S * 0.72), (W * 0.615, H - S * 0.55), S)
    return union(bowl, tail)


BUILDERS = {'0': build_zero, '4': build_four, '6': build_six}


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
        W = float(g0.xMax - g0.xMin)
        H = float(g0.yMax - g0.yMin)

        import inspect
        kw = dict(W=round(W), H=round(H))
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
    print('\n已重画 0 4 6:', os.path.basename(fp))


if __name__ == '__main__':
    import sys
    k = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    for f in FONTS:
        apply(f, k)
