#!/usr/bin/env python3
"""以「细体粗版」为底，做一套更强调手写感的字：徕卡手写体。

手法：
1. 每个字轻微旋转（±0.7°，按字码决定方向和角度，固定不随机）
2. 栅格上做一次闭运算，把转角再磨圆一点
3. 重新描摹回矢量，保留原有字宽与字距
"""
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

sys.path.insert(0, r"D:\P9徕卡水印工具\开发文件\tools")
import build_full3

BASE = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Bold.ttf"
DST = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Regular.ttf"
SIZE = 3000               # 渲染字号，cap ≈ 2100px
CAP = 700.0
MAX_TILT = 0.7            # 单字最大倾斜（度）
CLOSE_K = 5               # 闭运算核半径（像素）


def render(ch):
    f = ImageFont.truetype(BASE, SIZE)
    im = Image.new("L", (SIZE * 2, SIZE * 2), 0)
    ImageDraw.Draw(im).text((SIZE // 2, SIZE // 2), ch, font=f, fill=255)
    m = (np.array(im) > 127).astype(np.uint8)
    ys, xs = np.where(m)
    if len(ys) == 0:
        return None
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def tilt(mask, deg):
    mask = (mask * 255).astype(np.uint8)
    h, w = mask.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    cosv, sinv = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * sinv + w * cosv), int(h * cosv + w * sinv)
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    out = cv2.warpAffine(mask, M, (nw, nh), flags=cv2.INTER_LINEAR, borderValue=0)
    return (out > 127).astype(np.uint8)


def main():
    base = TTFont(BASE)
    base_cmap = base.getBestCmap()
    base_hmtx = base['hmtx']

    glyphs, order, adv = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    adv['.notdef'] = 500

    for cp, name in sorted(base_cmap.items()):
        ch = chr(cp)
        if ch == ' ':
            continue
        m = render(ch)
        if m is None:
            continue
        # 固定但略有差异的倾斜：按字符码决定方向
        deg = MAX_TILT * (1 if (cp % 3 == 0) else -1) * ((cp % 5) + 1) / 5.0
        m = tilt(m, deg)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CLOSE_K * 2 + 1, CLOSE_K * 2 + 1))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)

        cap_px = float(m.shape[0])
        cmds, ink_w = build_full3.vectorize(m, cap_px, None, CAP)
        if not cmds:
            continue
        tp = TTGlyphPen(None)
        for c, _ in cmds:
            for cmd in c:
                if cmd[0] == 'M':
                    tp.moveTo(cmd[1])
                elif cmd[0] == 'L':
                    tp.lineTo(cmd[1])
                elif cmd[0] == 'Q':
                    tp.qCurveTo(cmd[1], cmd[2])
                else:
                    tp.closePath()
        gname = 'uni%04X' % cp
        glyphs[gname] = tp.glyph()
        order.append(gname)
        adv[gname] = base_hmtx[name][0]
        print('  ', ch, end='', flush=True)

    print()
    from fontTools.fontBuilder import FontBuilder
    fb = FontBuilder(unitsPerEm=1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({cp: 'uni%04X' % cp for cp in base_cmap if 'uni%04X' % cp in glyphs})
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (adv[n], 0) for n in order})
    fb.setupHorizontalHeader(ascent=1000, descent=-300)
    fb.setupNameTable({
        'familyName': 'HWLeica Hand',
        'styleName': 'Regular',
        'uniqueFontIdentifier': 'HWLeicaHand-Regular',
        'fullName': 'HWLeica Hand Regular',
        'psName': 'HWLeicaHand-Regular',
    })
    fb.setupOS2(sTypoAscender=1000, sTypoDescender=-300, usWinAscent=1000, usWinDescent=300)
    fb.setupPost()
    fb.save(DST)
    print('saved', DST, os.path.getsize(DST) // 1024, 'KB, 字形', len(order))


if __name__ == '__main__':
    main()
