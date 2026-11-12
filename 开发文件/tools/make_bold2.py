#!/usr/bin/env python3
"""给两个字重各生成一个真 Bold（700），并按字形类别控制外扩量。

教训：统一外扩 11 单位会把 8 的字腔、句点、破折号撑成黑团，
所以按类别分级：
  普通字母 11 / 斜笔与 B 6 / 带字腔数字 6 / 标点符号 3
细体整体按比例缩到约 0.83。
"""
import os
import sys

import pathops
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

sys.path.insert(0, r"D:\P9徕卡水印工具\开发文件\tools")

CASES = [
    # (源文件, 输出文件, 家族名, 外扩比例)

    (r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
     r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Bold.ttf", 'HWLeica Light', 0.82),
]

DIAG = set('AKMNVWXYZ47B')
DIGIT_HOLE = set('0689')
PUNCT = set('?! /.:-="\'\\,;()[]{}|+=*&%#@_~`^<>')
CAP = 700.0


def offset_for(ch, k):
    if ch in PUNCT:
        base = 3.0
    elif ch in DIGIT_HOLE:
        base = 5.5
    elif ch in DIAG:
        base = 6.0
    elif ch.isdigit():
        base = 8.0
    else:
        base = 11.0
    return base * k


def offset_path(path, d):
    band = pathops.Path()
    band.addPath(path)
    band.stroke(d * 2.0, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
    band.convertConicsToQuads()
    out = pathops.op(path, band, pathops.PathOp.UNION, fix_winding=True)
    out.convertConicsToQuads()
    return out


def build(src, dst, family, k):
    font = TTFont(src)
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    glyf = font['glyf']
    hmtx = font['hmtx']

    for cp, name in cmap.items():
        ch = chr(cp)
        if ch == ' ':
            continue
        d = offset_for(ch, k)
        g0 = glyf[name]
        ref_y = g0.yMin if hasattr(g0, 'yMin') else 0
        ref_h = (g0.yMax - g0.yMin) if hasattr(g0, 'yMax') else CAP
        p = pathops.Path()
        gs[name].draw(p.getPen())
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
        # 只把外扩带来的高度变化还原回「原来的高度」，
        # 标点这类小字形不能被放大到 700
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
        adv, lsb = hmtx[name]
        hmtx[name] = (int(adv + 2 * d), lsb)

    nt = font['name']
    for rec in list(nt.names):
        if rec.nameID == 1:
            rec.string = family
        elif rec.nameID == 2:
            rec.string = 'Bold'
        elif rec.nameID == 4:
            rec.string = family + ' Bold'
        elif rec.nameID == 6:
            rec.string = family.replace(' ', '') + '-Bold'
        elif rec.nameID == 16:
            rec.string = family
        elif rec.nameID == 17:
            rec.string = 'Bold'
    font['OS/2'].usWeightClass = 700
    font['OS/2'].fsSelection = (font['OS/2'].fsSelection & ~0x40) | 0x20
    font['head'].macStyle |= 0x1
    font.save(dst)
    print('saved', os.path.basename(dst), os.path.getsize(dst) // 1024, 'KB')


def main():
    for src, dst, family, k in CASES:
        build(src, dst, family, k)


if __name__ == '__main__':
    main()
