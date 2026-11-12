#!/usr/bin/env python3
"""把字形上细小的缺口和凸起磨平。

做法是矢量上的「闭运算」：先外扩 r，再内缩 r。
小于 2r 的凸起会被削掉，小于 2r 的缺口会被填平，
整体轮廓与周围自然衔接，不会改变字形的比例。
"""
import os
import sys

import pathops
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib import TTFont

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Bold.ttf",
]
R = 6.0     # 磨平半径（单位）


def offset_path(path, d):
    band = pathops.Path()
    band.addPath(path)
    band.stroke(abs(d) * 2.0, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
    band.convertConicsToQuads()
    op = pathops.PathOp.UNION if d > 0 else pathops.PathOp.DIFFERENCE
    out = pathops.op(path, band, op, fix_winding=True)
    out.convertConicsToQuads()
    return out


def main():
    for fp in FONTS:
        font = TTFont(fp)
        cmap = font.getBestCmap()
        gs = font.getGlyphSet()
        glyf = font['glyf']
        n = 0
        for cp, name in sorted(cmap.items()):
            ch = chr(cp)
            if ch == ' ':
                continue
            g0 = glyf[name]
            if not hasattr(g0, 'yMax'):
                continue
            h = g0.yMax - g0.yMin
            if h < 120:          # 标点太小，跳过
                continue
            ref_y = float(g0.yMin)
            p = pathops.Path()
            gs[name].draw(p.getPen())
            try:
                out = offset_path(p, R)
                out = offset_path(out, -R)
            except Exception as e:
                print('  跳过', ch, e)
                continue
            tp = TTGlyphPen(None)
            cu = Cu2QuPen(tp, 0.8, reverse_direction=False)
            out.draw(cu)
            g = tp.glyph()
            g.recalcBounds(glyf)
            dy = ref_y - g.yMin
            if abs(dy) > 0.5:
                g.coordinates.translate((0, dy))
                g.recalcBounds(glyf)
            glyf[name] = g
            n += 1
        font.save(fp)
        print(os.path.basename(fp), '磨平', n, '个字形，', os.path.getsize(fp) // 1024, 'KB')


if __name__ == '__main__':
    main()
