#!/usr/bin/env python3
"""用常规字重生成真正的 Bold（700），替代浏览器的伪粗体。

做法：轮廓整体外扩 d 单位，再把字高拉回 700。
这样任何设备都按真实轮廓渲染，不会出现「P9 上参数被抹粗」的差异。
"""
import os

import cv2
import numpy as np
import pathops
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

SRC = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
DST = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Bold.ttf"
CAP = 700.0
OFFSET = 11.0          # 每侧外扩，笔画约 +22
# 斜笔在加粗后视觉上更重，单独少加一点
DIAG = set('AKMNVWXYZ47B')
OFFSET_DIAG = 6.0


def stroke_of(path, ch, size=1000):
    f = ImageFont.truetype(path, size)
    im = Image.new("L", (size * 2, size * 2), 0)
    ImageDraw.Draw(im).text((80, 80), ch, font=f, fill=255)
    m = (np.array(im) > 127).astype(np.uint8)
    if m.sum() == 0:
        return 0.0
    return float(cv2.distanceTransform(m, cv2.DIST_L2, 5).max()) * 2.0


def offset_path(path, d):
    band = pathops.Path()
    band.addPath(path)
    band.stroke(d * 2.0, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
    band.convertConicsToQuads()
    out = pathops.op(path, band, pathops.PathOp.UNION, fix_winding=True)
    out.convertConicsToQuads()
    return out


def main():
    font = TTFont(SRC)
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    glyf = font['glyf']

    for cp, name in cmap.items():
        ch = chr(cp)
        if ch == ' ':
            continue
        p = pathops.Path()
        gs[name].draw(p.getPen())
        d = OFFSET_DIAG if ch in DIAG else OFFSET
        try:
            out = offset_path(p, d)
        except Exception as e:
            print('  跳过', ch, e)
            continue
        tpen = TTGlyphPen(None)
        cu = Cu2QuPen(tpen, 0.8, reverse_direction=False)
        out.draw(cu)
        g = tpen.glyph()
        g.recalcBounds(glyf)

        # 外扩把字高撑大了，按比例拉回 0..700
        h = g.yMax - g.yMin
        if h > 10:
            k = CAP / h
            if abs(k - 1) > 0.002:
                tpen2 = TTGlyphPen(None)
                cu2 = Cu2QuPen(tpen2, 0.8, reverse_direction=False)
                from fontTools.pens.transformPen import TransformPen
                out.draw(TransformPen(cu2, (k, 0, 0, k, 0, -g.yMin * k)))
                g2 = tpen2.glyph()
                g2.recalcBounds(glyf)
                glyf[name] = g2
                continue
        glyf[name] = g

    # 名称与权重
    nt = font['name']
    for rec in list(nt.names):
        if rec.nameID == 1:
            rec.string = 'HWLeica'
        elif rec.nameID == 2:
            rec.string = 'Bold'
        elif rec.nameID == 4:
            rec.string = 'HWLeica Bold'
        elif rec.nameID == 6:
            rec.string = 'HWLeica-Bold'
        elif rec.nameID == 16:
            rec.string = 'HWLeica'
        elif rec.nameID == 17:
            rec.string = 'Bold'
    font['OS/2'].usWeightClass = 700
    font['OS/2'].fsSelection = (font['OS/2'].fsSelection & ~0x40) | 0x20  # BOLD
    font['head'].macStyle |= 0x1

    # 字距同步加宽，避免加粗后粘在一起
    hmtx = font['hmtx']
    for cp, name in cmap.items():
        adv, lsb = hmtx[name]
        hmtx[name] = (int(adv + 2 * (OFFSET_DIAG if ch in DIAG else OFFSET)), lsb)

    font.save(DST)
    print('saved', DST, os.path.getsize(DST) // 1024, 'KB')

    for ch in 'HMNO':
        a = stroke_of(SRC, ch)
        b = stroke_of(DST, ch)
        print(f'  {ch}: 常规 {a:.0f} → 粗体 {b:.0f}')


if __name__ == '__main__':
    main()
