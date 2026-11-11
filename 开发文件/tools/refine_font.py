#!/usr/bin/env python3
"""在抠图版字体上做精修：圆字 overshoot、光学字距、kerning。

1. 圆弧字（O C G Q S U o c e s）上下各溢出 1.2%，视觉上才和方块字等高
2. 按字形类别微调字宽：斜边字收紧、窄字放宽
3. 用 FEA 编译常见字距对
"""
import os

from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

SRC = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
DST = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Refined.ttf"

ROUND_CAP = set('OCGQSU')
ROUND_LOW = set('oces')
DIAGONAL = set('AVWYK')
NARROW = set('IJijl')

OVERSHOOT = 0.012

KERN = [
    ('A', 'V', -45), ('A', 'W', -40), ('A', 'Y', -50), ('A', 'T', -35),
    ('L', 'T', -40), ('L', 'V', -40), ('L', 'W', -35), ('L', 'Y', -45),
    ('P', 'A', -30), ('T', 'A', -35), ('V', 'A', -45), ('W', 'A', -40),
    ('Y', 'A', -50), ('T', 'o', -25), ('Y', 'o', -25), ('T', 'e', -20),
    ('F', 'A', -25), ('P', 'o', -15), ('r', '.', -25), ('f', '/', -15),
    ('/', '.', -15), ('Y', 'e', -20), ('V', 'o', -25), ('W', 'o', -20),
]


def glyph_cmds(font, name):
    gs = font.getGlyphSet()
    rec = DecomposingRecordingPen(gs)
    gs[name].draw(rec)
    return rec.value


def rebuild(font, name, scale_y, dy=0.0):
    """按基线缩放 y（实现 overshoot）"""
    rec = glyph_cmds(font, name)
    pen = TTGlyphPen(None)
    for op, args in rec:
        if op == 'closePath':
            pen.closePath()
            continue
        moved = []
        for p in args:
            if isinstance(p, tuple) and len(p) == 2:
                moved.append((p[0], p[1] * scale_y + dy))
            else:
                moved.append(p)
        getattr(pen, op)(*moved)
    return pen.glyph()


def main():
    font = TTFont(SRC)
    cmap = font.getBestCmap()
    glyf = font['glyf']
    hmtx = font['hmtx']

    # 1) overshoot
    changed = 0
    for ch in ROUND_CAP | ROUND_LOW:
        name = cmap.get(ord(ch))
        if not name:
            continue
        g = glyf[name]
        if getattr(g, 'numberOfContours', 0) <= 0:
            continue
        glyf[name] = rebuild(font, name, 1 + OVERSHOOT)
        changed += 1
    print('overshoot glyphs:', changed)

    # 2) 光学字距
    for ch in list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'):
        name = cmap.get(ord(ch))
        if not name:
            continue
        aw, lsb = hmtx[name]
        k = 1.0
        if ch in DIAGONAL:
            k = 0.97
        elif ch in ROUND_CAP or ch in ROUND_LOW:
            k = 0.985
        elif ch in NARROW:
            k = 1.04
        hmtx[name] = (int(round(aw * k)), int(lsb))

    # 3) kerning
    lines = ['feature kern {']
    for a, b, v in KERN:
        na, nb = cmap.get(ord(a)), cmap.get(ord(b))
        if not na or not nb:
            continue
        lines.append('  pos \\%s \\%s %d;' % (na, nb, v))
    lines.append('} kern;')
    fea = '\n'.join(lines)
    try:
        addOpenTypeFeaturesFromString(font, fea)
        print('kern pairs:', len(KERN))
    except Exception as e:
        print('kern failed:', e)

    font.save(DST)
    print('saved', DST, os.path.getsize(DST) // 1024, 'KB')


if __name__ == '__main__':
    main()
