#!/usr/bin/env python3
"""从现有 HWLeica 生成细体（Light）。

原理：把轮廓向内收缩 r 个单位。
实现：内缩 = 原形 − 轮廓描边(2r)，用 pathops 的布尔运算完成，
      再用 cu2qu 转回 TrueType 二次曲线。
"""
import os

import pathops
from fontTools.ttLib import TTFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

SRC = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
DST = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf"

INSET = 26          # 内缩量（units，em=1000）
FAMILY = 'HWLeica Light'


def to_pathops(glyph_set, name):
    p = pathops.Path()
    glyph_set[name].draw(p.getPen())
    return p


def erode(path, r):
    band = pathops.Path()
    band.addPath(path)
    band.stroke(2.0 * r, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
    band.convertConicsToQuads()
    out = pathops.op(path, band, pathops.PathOp.DIFFERENCE, fix_winding=True)
    out.convertConicsToQuads()
    return out


def main():
    font = TTFont(SRC)
    gs = font.getGlyphSet()
    glyf = font['glyf']
    hmtx = font['hmtx']
    names = font.getGlyphOrder()

    new = {}
    ok = 0
    for name in names:
        if name == '.notdef':
            continue
        g = glyf[name]
        if getattr(g, 'numberOfContours', 0) <= 0:
            new[name] = g
            continue
        try:
            path = to_pathops(gs, name)
            thin = erode(path, INSET)
            tpen = TTGlyphPen(None)
            cu = Cu2QuPen(tpen, 0.8, reverse_direction=False)
            thin.draw(cu)
            new[name] = tpen.glyph()
            ok += 1
        except Exception as e:
            print('  fail', name, e)
            new[name] = g
    print('thinned glyphs:', ok)

    for n, g in new.items():
        glyf[n] = g

    # 改名 + 字重 300
    nt = font['name']
    for rec in list(nt.names):
        if rec.nameID in (1, 16):
            rec.string = FAMILY
        elif rec.nameID in (2, 17):
            rec.string = 'Regular'
        elif rec.nameID == 4:
            rec.string = FAMILY + ' Regular'
        elif rec.nameID == 6:
            rec.string = 'HWLeicaLight-Regular'
    font['OS/2'].usWeightClass = 300

    font.save(DST)
    print('saved', DST, os.path.getsize(DST) // 1024, 'KB')


if __name__ == '__main__':
    main()
