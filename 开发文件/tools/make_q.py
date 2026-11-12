#!/usr/bin/env python3
"""重做 Q：源图里 Q 的尾巴画在了字腔内部，看着像 O。

做法：取 O 的轮廓，在右下角接一条圆头斜杠，用布尔并集合成 Q。
两套字（常规/细体）都替换。
"""
import os

import pathops
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
]

CAP = 700.0


def glyph_path(gs, name):
    p = pathops.Path()
    gs[name].draw(p.getPen())
    return p


def ink_bounds(path):
    b = path.bounds
    return b


def build_q(font, stem):
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    o_path = glyph_path(gs, cmap[ord('O')])
    x0, y0, x1, y1 = o_path.bounds
    w = x1 - x0
    h = y1 - y0

    # 尾巴：从字腔内右下角，斜穿出去
    sx = x0 + w * 0.58
    sy = y0 + h * 0.30
    ex = x1 + w * 0.10
    ey = y0 - h * 0.06

    tail = pathops.Path()
    pen = tail.getPen()
    pen.moveTo((sx, sy))
    pen.lineTo((ex, ey))
    tail.stroke(stem, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
    tail.convertConicsToQuads()

    q = pathops.op(o_path, tail, pathops.PathOp.UNION, fix_winding=True)
    q.convertConicsToQuads()
    return q


def main():
    for path in FONTS:
        font = TTFont(path)
        cmap = font.getBestCmap()
        glyf = font['glyf']
        hmtx = font['hmtx']
        gs = font.getGlyphSet()

        o_glyph = glyf[cmap[ord('O')]]
        # 用 O 的笔画厚度估算：环厚 = (宽度 - 字腔宽) / 2，这里直接取 1/7 宽
        stem = (o_glyph.xMax - o_glyph.xMin) / 7.0
        q = build_q(font, stem)

        # 归一化：高度对齐大写高，底边贴基线
        bx0, by0, bx1, by1 = q.bounds
        k = CAP / (by1 - by0)

        tpen = TTGlyphPen(None)
        cu = Cu2QuPen(tpen, 0.8, reverse_direction=False)

        class ScalePen:
            def __init__(self, inner, k, dy):
                self.inner = inner
                self.k = k
                self.dy = dy

            def moveTo(self, p): self.inner.moveTo((p[0] * self.k, (p[1] - by0) * self.k))
            def lineTo(self, p): self.inner.lineTo((p[0] * self.k, (p[1] - by0) * self.k))
            def qCurveTo(self, *pts): self.inner.qCurveTo(*[(p[0] * self.k, (p[1] - by0) * self.k) if p else None for p in pts])
            def curveTo(self, *pts): self.inner.curveTo(*[(p[0] * self.k, (p[1] - by0) * self.k) for p in pts])
            def closePath(self): self.inner.closePath()

        q.draw(ScalePen(cu, k, by0))

        adv, lsb = hmtx[cmap[ord('Q')]]
        gly = tpen.glyph()
        gly.recalcBounds(glyf)
        glyf[cmap[ord('Q')]] = gly

        # 字距：跟 O 一样，尾巴略微超出去
        o_adv = hmtx[cmap[ord('O')]][0]
        hmtx[cmap[ord('Q')]] = (int(o_adv + stem * 0.15), lsb)
        new = gly

        font.save(path)
        print(os.path.basename(path), 'Q 重建: 高度', new.yMax - new.yMin, '宽', new.xMax - new.xMin)


if __name__ == '__main__':
    main()
