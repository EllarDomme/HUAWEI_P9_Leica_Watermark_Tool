#!/usr/bin/env python3
"""以细体粗版为底，做「徕卡手写体」——矢量方式，不重新描摹。

每个字形：
1. 绕自身中心轻微旋转（±0.6°，按字符码固定）
2. 做一次「先外扩再内缩」的闭运算，把转角磨得更圆
3. 字高归位，字宽与字距沿用原字体
"""
import math
import os

import pathops
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

BASE = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Bold.ttf"
DST = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Regular.ttf"
CAP = 700.0
MAX_TILT = 0.6
ROUND = 0.0          # 不磨圆（避免吃掉小字腔）


def offset_path(path, d):
    band = pathops.Path()
    band.addPath(path)
    band.stroke(abs(d) * 2.0, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
    band.convertConicsToQuads()
    op = pathops.PathOp.UNION if d > 0 else pathops.PathOp.DIFFERENCE
    out = pathops.op(path, band, op, fix_winding=True)
    out.convertConicsToQuads()
    return out


def handify(path, deg):
    # 绕 bbox 中心旋转
    x0, y0, x1, y1 = path.bounds
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    rot = pathops.Path()
    pen = rot.getPen()
    path.draw(TransformPen(pen, (ca, sa, -sa, ca,
                                 cx - ca * cx + sa * cy,
                                 cy - sa * cx - ca * cy)))
    rot.convertConicsToQuads()
    if ROUND <= 0:
        return rot
    out = offset_path(rot, ROUND)
    out = offset_path(out, -ROUND)
    return out


def main():
    font = TTFont(BASE)
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    glyf = font['glyf']
    hmtx = font['hmtx']

    for cp, name in sorted(cmap.items()):
        ch = chr(cp)
        if ch == ' ':
            continue
        g0 = glyf[name]
        if not hasattr(g0, 'yMax'):
            continue
        ref_h = g0.yMax - g0.yMin
        ref_y = g0.yMin

        p = pathops.Path()
        gs[name].draw(p.getPen())
        deg = MAX_TILT * (1 if cp % 2 == 0 else -1) * ((cp % 4) + 2) / 5.0
        try:
            out = handify(p, deg)
        except Exception as e:
            print('  跳过', ch, e)
            continue

        # 高度归一，保留原字高与基线
        tpen = TTGlyphPen(None)
        cu = Cu2QuPen(tpen, 0.8, reverse_direction=False)
        out.draw(cu)
        g = tpen.glyph()
        g.recalcBounds(glyf)
        h = g.yMax - g.yMin
        if h > 5 and ref_h > 5:
            s = ref_h / h
            if abs(s - 1) > 0.002:
                tpen2 = TTGlyphPen(None)
                cu2 = Cu2QuPen(tpen2, 0.8, reverse_direction=False)
                out.draw(TransformPen(cu2, (s, 0, 0, s, 0, ref_y - g.yMin * s)))
                g = tpen2.glyph()
                g.recalcBounds(glyf)
        glyf[name] = g
        print(' ', ch, end='', flush=True)

    nt = font['name']
    for rec in list(nt.names):
        if rec.nameID == 1:
            rec.string = 'HWLeica Hand'
        elif rec.nameID == 4:
            rec.string = 'HWLeica Hand Regular'
        elif rec.nameID == 6:
            rec.string = 'HWLeicaHand-Regular'
        elif rec.nameID == 16:
            rec.string = 'HWLeica Hand'
    font.save(DST)
    print('\nsaved', DST, os.path.getsize(DST) // 1024, 'KB')


if __name__ == '__main__':
    main()
