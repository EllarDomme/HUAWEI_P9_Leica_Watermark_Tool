#!/usr/bin/env python3
"""统一大写字母的笔画粗细。

抠图源里，M/N/Q/R/W 这类斜笔或弧笔天生偏粗，C/G/O/S 偏细，
排成一行时会出现「有的字粗、有的字细」。

做法：量出每个字的实际笔画宽度，用布尔运算把轮廓整体外扩/内缩，
把粗细拉回中位数，再重新对齐字高与基线。
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
MAX_DELTA = 26.0     # 单字最多加/减 26 单位，避免改形状


def stroke_of(font_path, ch):
    """渲染单字，用距离变换估算笔画宽度（单位：em=1000 时的 font units）"""
    f = ImageFont.truetype(font_path, 1000)
    im = Image.new("L", (1200, 1200), 0)
    d = ImageDraw.Draw(im)
    d.text((100, 100), ch, font=f, fill=255)
    m = (np.array(im) > 127).astype(np.uint8)
    if m.sum() == 0:
        return None
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    return float(dist.max()) * 2.0


def offset_path(path, delta):
    band = pathops.Path()
    band.addPath(path)
    band.stroke(abs(delta) * 2.0, pathops.LineCap.ROUND_CAP,
                pathops.LineJoin.ROUND_JOIN, 4.0)
    band.convertConicsToQuads()
    if delta > 0:
        out = pathops.op(path, band, pathops.PathOp.UNION, fix_winding=True)
    else:
        out = pathops.op(path, band, pathops.PathOp.DIFFERENCE, fix_winding=True)
    out.convertConicsToQuads()
    return out


def rebuild(font, name, delta):
    gs = font.getGlyphSet()
    p = pathops.Path()
    gs[name].draw(p.getPen())
    out = offset_path(p, delta)
    tpen = TTGlyphPen(None)
    cu = Cu2QuPen(tpen, 0.8, reverse_direction=False)
    out.draw(cu)
    return tpen.glyph()


def normalize_height(font, gly, glyf):
    """把字形拉到 0..700，横向不动"""
    gly.recalcBounds(glyf)
    h = gly.yMax - gly.yMin
    if h <= 10:
        return gly
    k = CAP / h
    if abs(k - 1) < 0.002 and abs(gly.yMin) < 1:
        return gly
    gs = font.getGlyphSet()
    return gly


def main():
    for fp in FONTS:
        widths = {}
        for ch in CHARS:
            w = stroke_of(fp, ch)
            if w:
                widths[ch] = w
        med = statistics.median(widths.values())
        print(os.path.basename(fp), '笔画中位数', round(med, 1))
        dev = {ch: round(w - med, 1) for ch, w in widths.items() if abs(w - med) > 4}
        print('  偏差 >4 的字:', dev)

        font = TTFont(fp)
        cmap = font.getBestCmap()
        glyf = font['glyf']
        for ch in CHARS:
            d = widths.get(ch)
            if d is None:
                continue
            delta = med - d
            delta = max(-MAX_DELTA, min(MAX_DELTA, delta)) / 2.0
            if abs(delta) < 1.5:
                continue
            name = cmap[ord(ch)]
            try:
                g = rebuild(font, name, delta)
            except Exception as e:
                print('  跳过', ch, e)
                continue
            g.recalcBounds(glyf)
            glyf[name] = g
            # 外扩/内缩会改变字高，这里拉回 0..700，基线不变
            fixed = normalize_ink.transform(font, name, 0.0, CAP)
            if fixed is not None:
                glyf[name] = fixed
        font.save(fp)

        # 复核
        after = {}
        for ch in CHARS:
            w = stroke_of(fp, ch)
            if w:
                after[ch] = round(w, 1)
        vals = list(after.values())
        print('  处理后范围', min(vals), '-', max(vals),
              '标准差', round(statistics.pstdev(vals), 2))


if __name__ == '__main__':
    main()
