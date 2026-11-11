#!/usr/bin/env python3
"""按徕卡刻字复刻图生成单线字体原型：等宽笔画 + 圆角 + 平头。

坐标：em 1000，基线 0，字高 700，笔画宽 92。
字形用「骨架折线描边」生成轮廓（skia-pathops 提供 stroke）。
"""
import math
import os
import sys

import pathops
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

W = 92            # 笔画宽度
CAP = 700         # 字高
ADV = 600         # 默认字宽
EM = 1000

def poly(points, closed=False):
    p = pathops.Path()
    p.moveTo(*points[0])
    for pt in points[1:]:
        p.lineTo(*pt)
    if closed:
        p.close()
    return p

def rect(x0, y0, x1, y1):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True)

def circle(cx, cy, r, n=48):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return poly(pts, closed=True)

def roundrect(x0, y0, x1, y1, r):
    pts = []
    corners = [((x1 - r, y1 - r), 0), ((x0 + r, y1 - r), 90), ((x0 + r, y0 + r), 180), ((x1 - r, y0 + r), 270)]
    for (cx, cy), a0 in corners:
        for i in range(13):
            a = math.radians(a0 + 90 * i / 12)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return poly(pts, closed=True)

def stroke_path(p):
    p.stroke(W, pathops.LineCap.BUTT_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
    p.convertConicsToQuads()
    return p

# ---- 骨架定义：每个字形返回若干轮廓（stroke 后的 Path）----
def g0():
    return [roundrect(160, 60, 460, 640, 120)]

def g1():
    return [stroke_path(poly([(300, 60), (300, 640)])), stroke_path(poly([(200, 520), (300, 630)]))]

def g2():
    return [stroke_path(poly([(150, 600), (300, 650), (430, 560), (150, 90), (450, 90)]))]

def g3():
    return [stroke_path(poly([(150, 650), (450, 650)])),
            stroke_path(poly([(450, 650), (450, 60)])),
            stroke_path(poly([(150, 60), (450, 60)])),
            stroke_path(poly([(200, 350), (430, 350)]))]

def g4():
    return [stroke_path(poly([(430, 650), (430, 40)])),
            stroke_path(poly([(430, 650), (150, 260)])),
            stroke_path(poly([(120, 260), (480, 260)]))]

def g5():
    return [stroke_path(poly([(450, 650), (150, 650)])),
            stroke_path(poly([(150, 650), (150, 390)])),
            stroke_path(poly([(150, 390), (350, 390)])),
            stroke_path(poly([(350, 390), (440, 320), (440, 140), (360, 60), (150, 60)]))]

def g6():
    return [stroke_path(poly([(430, 620), (300, 660), (170, 620), (120, 480), (120, 150),
                              (180, 70), (320, 60), (440, 110), (460, 240), (400, 330), (250, 350), (140, 320)]))]

def g7():
    return [stroke_path(poly([(140, 650), (460, 650)])),
            stroke_path(poly([(460, 650), (200, 40)]))]

def g8():
    return [roundrect(150, 375, 450, 650, 110), roundrect(150, 50, 450, 320, 105)]

def g9():
    return [stroke_path(poly([(170, 90), (300, 50), (430, 90), (480, 230), (480, 560),
                              (420, 640), (280, 650), (160, 600), (140, 470), (200, 380), (350, 360), (460, 390)]))]

def gA():
    return [stroke_path(poly([(140, 60), (300, 650), (460, 60)])),
            stroke_path(poly([(200, 300), (400, 300)]))]

def gC():
    return [stroke_path(poly([(450, 590), (340, 650), (190, 640), (120, 560), (120, 140),
                              (190, 60), (340, 50), (450, 110)]))]

def gE():
    return [stroke_path(poly([(450, 650), (150, 650)])),
            stroke_path(poly([(150, 650), (150, 60)])),
            stroke_path(poly([(150, 60), (450, 60)])),
            stroke_path(poly([(150, 360), (400, 360)]))]

def gH():
    return [stroke_path(poly([(150, 650), (150, 60)])),
            stroke_path(poly([(450, 650), (450, 60)])),
            stroke_path(poly([(150, 360), (450, 360)]))]

def gI():
    return [stroke_path(poly([(300, 650), (300, 60)]))]

def gL():
    return [stroke_path(poly([(160, 650), (160, 60)])),
            stroke_path(poly([(160, 60), (450, 60)]))]

def gM():
    return [stroke_path(poly([(120, 60), (120, 650)])),
            stroke_path(poly([(120, 650), (300, 260)])),
            stroke_path(poly([(300, 260), (480, 650)])),
            stroke_path(poly([(480, 650), (480, 60)]))]

def gP():
    return [stroke_path(poly([(160, 60), (160, 650)])),
            stroke_path(poly([(160, 650), (340, 650), (440, 570), (440, 400), (340, 320), (160, 320)]))]

def gS():
    return [stroke_path(poly([(450, 590), (350, 650), (190, 645), (130, 570), (140, 470),
                              (220, 410), (350, 360), (430, 290), (430, 150), (350, 60),
                              (190, 55), (120, 110)]))]

def gU():
    return [stroke_path(poly([(150, 650), (150, 150), (220, 65), (370, 65), (450, 150), (450, 650)]))]

def gX():
    return [stroke_path(poly([(140, 650), (460, 60)])),
            stroke_path(poly([(140, 60), (460, 650)]))]

def gslash():
    return [stroke_path(poly([(450, 650), (150, 40)]))]

def gdot():
    return [roundrect(250, 40, 340, 130, 18)]

def gcolon():
    return [roundrect(250, 40, 340, 130, 18), roundrect(250, 300, 340, 390, 18)]

def gdash():
    return [stroke_path(poly([(170, 350), (430, 350)]))]

GLYPHS = {
    'zero': g0, 'one': g1, 'two': g2, 'three': g3, 'four': g4, 'five': g5,
    'six': g6, 'seven': g7, 'eight': g8, 'nine': g9,
    'A': gA, 'C': gC, 'E': gE, 'H': gH, 'I': gI, 'L': gL, 'M': gM, 'P': gP,
    'S': gS, 'U': gU, 'X': gX,
    'slash': gslash, 'period': gdot, 'colon': gcolon, 'hyphen': gdash,
}
CMAP = {
    '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
    '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine',
    'A': 'A', 'C': 'C', 'E': 'E', 'H': 'H', 'I': 'I', 'L': 'L', 'M': 'M',
    'P': 'P', 'S': 'S', 'U': 'U', 'X': 'X',
    '/': 'slash', '.': 'period', ':': 'colon', '-': 'hyphen',
}

def to_pen(path):
    pen = TTGlyphPen(None)
    for verb, pts in path.segments:
        if verb == 'moveTo':
            pen.moveTo(pts[0])
        elif verb == 'lineTo':
            pen.lineTo(pts[0])
        elif verb == 'qCurveTo':
            pen.qCurveTo(*pts)
        elif verb == 'curveTo':
            pen.curveTo(*pts)
        elif verb == 'closePath':
            pen.closePath()
    return pen

def build(out_ttf):
    order = ['.notdef'] + list(GLYPHS.keys())
    fb = FontBuilder(EM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({ord(k): v for k, v in CMAP.items()})

    glyphs = {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()

    for name, fn in GLYPHS.items():
        parts = fn()
        if len(parts) == 1:
            outline = parts[0]
        else:
            combined = pathops.Path()
            for part in parts:
                combined.addPath(part)
            outline = pathops.simplify(combined)
        glyphs[name] = to_pen(outline).glyph()

    fb.setupGlyf(glyphs)
    metrics = {n: (ADV if n not in ('.notdef',) else ADV, 40) for n in order}
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({'familyName': 'LeicaLine', 'styleName': 'Regular',
                       'uniqueFontIdentifier': 'LeicaLine-Regular',
                       'fullName': 'LeicaLine', 'psName': 'LeicaLine-Regular',
                       'version': 'Version 1.0'})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.save(out_ttf)
    return out_ttf

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'LeicaLine.ttf'
    build(out)
    print('built', out, os.path.getsize(out) // 1024, 'KB')
