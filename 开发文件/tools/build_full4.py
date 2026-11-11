#!/usr/bin/env python3
"""用几何骨架重画几个容易走形的字（M W N K），保持与提取版一致的笔画宽度。

笔画宽度取 'H' 的实测（约 0.145×字高），圆角接头、平头端点，
和素材里那种“刻字”观感一致，但比像素描摹更规整。
"""
import os
import sys

import cv2
import numpy as np
import pathops
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_full3 import harvest, CAP, GAP, EM, XH

OUT = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
W = 100          # 笔画宽度（units）
SLANT = 0.0


def poly(pts, closed=False):
    p = pathops.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if closed:
        p.close()
    return p


def stroked(path, width=W):
    path.stroke(width, pathops.LineCap.BUTT_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
    path.convertConicsToQuads()
    return path


def skeleton_glyphs():
    """返回 {字符: 骨架折线列表}，坐标 0..700，宽度 0..620"""
    g = {}
    g['M'] = [[(120, 0), (120, 620), (330, 250), (540, 620), (540, 0)]]
    g['W'] = [[(120, 620), (120, 0), (330, 380), (540, 0), (540, 620)]]
    g['N'] = [[(120, 0), (120, 620), (540, 0), (540, 620)]]
    g['K'] = [[(120, 0), (120, 620)], [(120, 300), (520, 620)], [(120, 300), (520, 0)]]
    g['V'] = [[(120, 620), (330, 0), (540, 620)]]
    g['A'] = [[(120, 0), (330, 620), (540, 0)], [(200, 240), (460, 240)]]
    return g


def build_skeleton(char, strokes):
    p = pathops.Path()
    p.fillType = pathops.FillType.WINDING
    for line in strokes:
        part = poly([(x * 600.0 / 620.0 + 10, y * 700.0 / 620.0) for x, y in line])
        part = stroked(part)
        p.addPath(part)
    p.simplify()
    p.convertConicsToQuads()

    tpen = TTGlyphPen(None)
    cu = Cu2QuPen(tpen, 0.6, reverse_direction=False)
    p.draw(cu)
    return tpen.glyph()


def traced_glyph(ch, crop, baseline, cap_px):
    from build_full3 import vectorize
    target = XH if (ch.islower() and ch not in 'bdfhklt') else CAP
    cmds_list, width = vectorize(crop, cap_px, baseline, target)
    tpen = TTGlyphPen(None)
    for cmds, _ in cmds_list:
        for cmd in cmds:
            if cmd[0] == 'M':
                tpen.moveTo(cmd[1])
            elif cmd[0] == 'L':
                tpen.lineTo(cmd[1])
            elif cmd[0] == 'Q':
                tpen.qCurveTo(cmd[1], cmd[2])
            else:
                tpen.closePath()
    return tpen.glyph(), width


def main():
    crops = harvest()
    cap_px = float(np.median([crops[c][0].shape[0] for c in 'AHE']))
    skel = skeleton_glyphs()

    glyphs, order, adv = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    adv['.notdef'] = 500

    for ch in sorted(crops):
        crop, baseline = crops[ch]
        if ch in skel:
            try:
                glyphs['uni%04X' % ord(ch)] = build_skeleton(ch, skel[ch])
                order.append('uni%04X' % ord(ch))
                adv['uni%04X' % ord(ch)] = int(round(620 + CAP * GAP))
                print('  rebuilt', ch)
                continue
            except Exception as e:
                print('  skeleton failed', ch, e)
        try:
            glyph, width = traced_glyph(ch, crop, baseline, cap_px)
        except Exception as e:
            print('  traced failed', ch, e)
            continue
        glyphs['uni%04X' % ord(ch)] = glyph
        order.append('uni%04X' % ord(ch))
        adv['uni%04X' % ord(ch)] = int(round(width + CAP * GAP))

    tpen = TTGlyphPen(None)
    glyphs['space'] = tpen.glyph()
    order.append('space')
    adv['space'] = int(CAP * 0.30)

    fb = FontBuilder(EM, isTTF=True)
    fb.setupGlyphOrder(order)
    cmap = {ord(ch): 'uni%04X' % ord(ch) for ch in crops if 'uni%04X' % ord(ch) in glyphs}
    cmap[0x20] = 'space'
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (adv[n], 0) for n in order})
    fb.setupHorizontalHeader(ascent=int(CAP * 1.2), descent=-int(CAP * 0.3))
    fb.setupNameTable({'familyName': 'HWLeica', 'styleName': 'Regular',
                       'uniqueFontIdentifier': 'HWLeica-Regular', 'fullName': 'HWLeica',
                       'psName': 'HWLeica-Regular', 'version': 'Version 4.1'})
    fb.setupOS2(sTypoAscender=int(CAP * 1.2), sTypoDescender=-int(CAP * 0.3),
                usWinAscent=int(CAP * 1.2), usWinDescent=int(CAP * 0.3))
    fb.setupPost()
    fb.save(OUT)
    print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')


if __name__ == '__main__':
    main()
