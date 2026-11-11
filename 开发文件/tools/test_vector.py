#!/usr/bin/env python3
"""验证骨架描边效果：从素材里取几个字，做成临时字体并渲染。"""
import os
import sys

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skeleton_font import vectorize

SRC = r"E:\DeskTop\字体素材\20261111-193341.png"
CAP = 700


def rows_cols(m):
    act = (m > 0).sum(axis=1) > 0
    bands, start, gap = [], None, 0
    for y, a in enumerate(act):
        if a:
            if start is None:
                start = y
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= 8:
                bands.append((start, y - gap))
                start, gap = None, 0
    return bands


def blocks(m, y0, y1):
    band = m[y0:y1 + 1]
    bh = y1 - y0 + 1
    n, labels, stats, _ = cv2.connectedComponentsWithStats((band > 0).astype(np.uint8), 8)
    boxes = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 40 and h < 0.35 * bh:
            continue
        boxes.append([x, x + w - 1])
    boxes.sort()
    merged = []
    for b in boxes:
        if merged and b[0] <= merged[-1][1] + 3:
            merged[-1][1] = max(merged[-1][1], b[1])
        else:
            merged.append(list(b))
    return merged


def main():
    g = cv2.imread(SRC, 0)
    _, m = cv2.threshold(g, 150, 255, cv2.THRESH_BINARY)
    bands = [b for b in rows_cols(m) if b[1] - b[0] > 100]
    # 第三行 SUMILXPH
    y0, y1 = bands[2]
    texts = 'SUMILXPH'
    bs = blocks(m, y0, y1)
    print('blocks', len(bs), 'chars', len(texts))

    glyphs, order, adv = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    adv['.notdef'] = 500
    cap_px = y1 - y0 + 1

    for ch, (x0, x1) in zip(texts, bs):
        crop = m[y0:y1 + 1, x0:x1 + 1]
        ys, xs = np.where(crop > 0)
        crop = crop[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        path, w = vectorize(crop)
        k = CAP / float(cap_px)
        H = crop.shape[0]
        tpen = TTGlyphPen(None)
        cu = Cu2QuPen(tpen, 0.6, reverse_direction=False)
        for verb, pts in path.segments:
            scaled = [(p[0] * k, (H - p[1]) * k) for p in pts]
            if verb == 'moveTo':
                cu.moveTo(scaled[0])
            elif verb == 'lineTo':
                cu.lineTo(scaled[0])
            elif verb in ('qCurveTo', 'curveTo'):
                getattr(cu, verb)(*scaled)
            elif verb == 'closePath':
                cu.closePath()
        name = 'uni%04X' % ord(ch)
        glyphs[name] = tpen.glyph()
        order.append(name)
        adv[name] = int(round(crop.shape[1] * k + CAP * 0.13))
        print(ch, 'stroke', round(w, 1))

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({ord(c): 'uni%04X' % ord(c) for c in texts})
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (adv[n], 0) for n in order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({'familyName': 'SkelTest', 'styleName': 'Regular',
                       'uniqueFontIdentifier': 'SkelTest-Regular', 'fullName': 'SkelTest',
                       'psName': 'SkelTest-Regular', 'version': '1.0'})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    out = r"E:\DeskTop\_skel.ttf"
    fb.save(out)
    print('saved', out)

    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(out, 90)
    im = Image.new("RGB", (900, 160), (18, 18, 18))
    d = ImageDraw.Draw(im)
    d.text((20, 20), texts, font=f, fill=(240, 240, 238))
    im.save(r"E:\DeskTop\_skel.png")


if __name__ == '__main__':
    main()
