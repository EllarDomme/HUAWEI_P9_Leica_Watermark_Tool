#!/usr/bin/env python3
"""统一大写字母笔画粗细（迭代收敛版）。

每次按当前实测笔画宽度算出偏移量，外扩/内缩后再把字高拉回 700，
重复 3 轮直到粗细接近目标。避免一次改过头。
"""
import os
import statistics
import sys

import cv2
import numpy as np
import pathops
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

sys.path.insert(0, r"D:\P9徕卡水印工具\开发文件\tools")
import normalize_ink

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
]
CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CAP = 700.0
TOL = 3.5
MAX_OFFSET = 15.0     # 单次最多偏移 15 单位


def stroke_now(font_path, ch):
    f = ImageFont.truetype(font_path, 1000)
    im = Image.new("L", (1200, 1200), 0)
    ImageDraw.Draw(im).text((100, 100), ch, font=f, fill=255)
    m = (np.array(im) > 127).astype(np.uint8)
    if m.sum() == 0:
        return None
    return float(cv2.distanceTransform(m, cv2.DIST_L2, 5).max()) * 2.0


def offset_path(path, delta):
    band = pathops.Path()
    band.addPath(path)
    band.stroke(abs(delta) * 2.0, pathops.LineCap.ROUND_CAP,
                pathops.LineJoin.ROUND_JOIN, 4.0)
    band.convertConicsToQuads()
    op = pathops.PathOp.UNION if delta > 0 else pathops.PathOp.DIFFERENCE
    out = pathops.op(path, band, op, fix_winding=True)
    out.convertConicsToQuads()
    return out


def apply(font, name, delta):
    gs = font.getGlyphSet()
    p = pathops.Path()
    gs[name].draw(p.getPen())
    out = offset_path(p, delta)
    tpen = TTGlyphPen(None)
    cu = Cu2QuPen(tpen, 0.8, reverse_direction=False)
    out.draw(cu)
    g = tpen.glyph()
    glyf = font['glyf']
    g.recalcBounds(glyf)
    glyf[name] = g
    fixed = normalize_ink.transform(font, name, 0.0, CAP)
    if fixed is not None:
        glyf[name] = fixed


def main():
    for fp in FONTS:
        base = [stroke_now(fp, ch) for ch in CHARS]
        base = [b for b in base if b]
        target = statistics.median(base)
        print(os.path.basename(fp), '目标笔画', round(target, 1))

        font = TTFont(fp)
        cmap = font.getBestCmap()
        for ch in CHARS:
            name = cmap[ord(ch)]
            for _ in range(3):
                s = stroke_now(fp, ch)
                if s is None or abs(s - target) <= TOL:
                    break
                # 补偿：偏移后会被字高归一化按比例缩放
                # 只加粗偏细的字，偏粗的（M/N/R/W 的斜笔）不动，
                # 否则会把竖笔一起削细，形状就毁了
                if s > target - TOL:
                    break
                d = CAP * (target - s) / (2 * CAP - 2 * target)
                d = max(0.0, min(MAX_OFFSET, d))
                if abs(d) < 0.8:
                    break
                apply(font, name, d)
                font.save(fp)
        font.save(fp)

        after = [stroke_now(fp, ch) for ch in CHARS]
        after = [a for a in after if a]
        print('  处理后 范围 %.1f-%.1f 标准差 %.2f' % (
            min(after), max(after), statistics.pstdev(after)))


if __name__ == '__main__':
    main()
