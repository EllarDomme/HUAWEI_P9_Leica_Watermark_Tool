#!/usr/bin/env python3
"""徕卡手写体：每个字都有轻微的“歪七扭八”，但整体仍然工整。

逐字施加（都由字符码决定，同一台机器每次结果相同）：
  旋转 ±1.4°    /\  上下偏移 ±4 单位   /\  缩放 0.98–1.02   /\  横向轻微倾斜 ±0.02
字距也做 ±4 单位的小抖动，避免整行像打字机。
"""
import math
import os
import random

import pathops
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

BASE = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Bold.ttf"
DST = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Regular.ttf"

TILT = 1.4        # 最大旋转（度）
DY = 4.0          # 上下偏移（单位）
SC = 0.02         # 缩放浮动
SKEW = 0.02       # 横向倾斜
ADV_JIT = 4.0     # 字距抖动


def rng_for(cp):
    return random.Random(cp * 977 + 13)


def transform_path(path, params):
    x0, y0, x1, y1 = path.bounds
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    deg, dy, s, skew = params
    a = math.radians(deg)
    ca, sa = math.cos(a) * s, math.sin(a) * s
    # 先缩放/横向倾斜，再绕中心旋转，最后整体平移
    m = (ca, sa, -sa + skew, ca, 0.0, 0.0)
    out = pathops.Path()
    pen = out.getPen()

    def mapped(p):
        x, y = p[0] - cx, p[1] - cy
        X = m[0] * x + m[2] * y
        Y = m[1] * x + m[3] * y
        return (X + cx, Y + cy + dy)

    class Pen:
        def moveTo(self, p): pen.moveTo(mapped(p))
        def lineTo(self, p): pen.lineTo(mapped(p))
        def qCurveTo(self, *pts): pen.qCurveTo(*[mapped(p) if p else None for p in pts])
        def curveTo(self, *pts): pen.curveTo(*[mapped(p) for p in pts])
        def closePath(self): pen.closePath()

    path.draw(Pen())
    out.convertConicsToQuads()
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
        r = rng_for(cp)
        params = (r.uniform(-TILT, TILT), r.uniform(-DY, DY),
                  r.uniform(1 - SC, 1 + SC), r.uniform(-SKEW, SKEW))
        p = pathops.Path()
        gs[name].draw(p.getPen())
        try:
            out = transform_path(p, params)
        except Exception as e:
            print('  跳过', ch, e)
            continue
        tpen = TTGlyphPen(None)
        cu = Cu2QuPen(tpen, 0.8, reverse_direction=False)
        out.draw(cu)
        g = tpen.glyph()
        g.recalcBounds(glyf)
        glyf[name] = g
        adv, lsb = hmtx[name]
        hmtx[name] = (int(adv + r.uniform(-ADV_JIT, ADV_JIT)), lsb)
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
