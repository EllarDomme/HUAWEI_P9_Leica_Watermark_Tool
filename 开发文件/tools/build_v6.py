#!/usr/bin/env python3
"""从「字符抠图高清版」重建字体（potrace 曲线版）。

- 用 PNG 的 alpha 通道取字形（抠图边缘最准）
- potrace 直接输出贝塞尔曲线，不是多边形
- 大写字高统一 700，基线统一 0，字距按墨宽 + 间隙
"""
import os
import sys
import glob

import cv2
import numpy as np
import potrace
from fontTools.ttLib import TTFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

SRC = r"E:\DeskTop\字符抠图高清版\chars"
OUT = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
REF = r"D:\P9徕卡水印工具\开发文件\fonts\RoundCustom-原始.ttf"

EM, CAP, XH = 1000, 700, 500
GAP = 0.17
DESC = set('gjpqy')
SYMBOLS = {
    'backslash': '\\', 'colon': ':', 'dash': '-', 'dot': '.', 'doublequote': '"',
    'equal': '=', 'exclaim': '!', 'question': '?', 'singlequote': "'", 'slash': '/',
}


def load_mask(path):
    raw = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if raw is None:
        return None
    if raw.ndim == 3 and raw.shape[2] == 4:
        gray = raw[:, :, 3]
    else:
        g = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        gray = 255 - g if np.median(g) > 128 else g
    _, m = cv2.threshold(gray, 110, 255, cv2.THRESH_BINARY)
    n, lab, st, _ = cv2.connectedComponentsWithStats((m > 0).astype(np.uint8), 8)
    if n <= 1:
        return None
    big = st[1:, 4].max()
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] >= max(30, 0.02 * big):
            keep[lab == i] = 255
    ys, xs = np.where(keep > 0)
    if not len(xs):
        return None
    return keep[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def trace(path, scale, baseline_px):
    """返回 (命令序列, 墨宽)"""
    m = load_mask(path)
    if m is None:
        return None, 0
    bmp = potrace.Bitmap(m > 0)
    path_obj = bmp.trace(turdsize=2, alphamax=1.0, opticurve=True, opttolerance=0.25)

    h = m.shape[0]

    def T(p):
        return (p.x * scale, (baseline_px - p.y) * scale)

    cmds = []
    for curve in path_obj:
        cmds.append(('M', T(curve.start_point)))
        for seg in curve.segments:
            end = T(seg.end_point)
            if hasattr(seg, 'c1'):
                cmds.append(('C', T(seg.c1), T(seg.c2), end))
            else:
                # 二次控制点
                cmds.append(('C', T(seg.c), T(seg.c), end))
        cmds.append(('Z',))
    return cmds, m.shape[1]


def main():
    files = []
    for sub in ('upper', 'lower', 'digit'):
        d = os.path.join(SRC, sub)
        for n in sorted(os.listdir(d)):
            if n.endswith('.png'):
                files.append((n[:-4], os.path.join(d, n)))
    d = os.path.join(SRC, 'symbol')
    for n in sorted(os.listdir(d)):
        if n.endswith('.png'):
            ch = SYMBOLS.get(n[:-4])
            if ch:
                files.append((ch, os.path.join(d, n)))

    # 先量各类字高，确定缩放与基线
    caps = []
    xh = []
    for ch, p in files:
        m = load_mask(p)
        if m is None:
            continue
        if ch.isupper() or ch.isdigit():
            caps.append(m.shape[0])
        elif ch in 'aeomnrscuvwxz':
            xh.append(m.shape[0])
    cap_px = float(np.median(caps))
    xh_px = float(np.median(xh)) if xh else cap_px * 0.72
    print('cap px', cap_px, 'x-height px', xh_px)

    scale_up = CAP / cap_px
    scale_low = XH / xh_px

    glyphs, order, adv = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    adv['.notdef'] = 500

    for ch, p in files:
        m = load_mask(p)
        if m is None:
            continue
        is_low = ch.islower() and ch not in 'bdfhklt'
        scale = scale_low if is_low else scale_up
        # 基线：底部（下伸字母需要减去下伸量）
        # 基线：一般人取底部；下伸字母往下留 21% 字高
        baseline_px = float(m.shape[0])
        if ch in DESC:
            baseline_px = m.shape[0] - 0.21 * cap_px
        cmds, ink_w = trace(p, scale, baseline_px)
        if not cmds:
            continue

        tpen = TTGlyphPen(None)
        cu = Cu2QuPen(tpen, 0.8, reverse_direction=False)
        for cmd in cmds:
            if cmd[0] == 'M':
                cu.moveTo(cmd[1])
            elif cmd[0] == 'C':
                cu.curveTo(cmd[1], cmd[2], cmd[3])
            else:
                cu.closePath()

        name = 'uni%04X' % ord(ch)
        try:
            glyphs[name] = tpen.glyph()
        except Exception as e:
            print('  fail', ch, e)
            continue
        order.append(name)
        adv[name] = int(round(ink_w * scale + CAP * GAP))

    tpen = TTGlyphPen(None)
    glyphs['space'] = tpen.glyph()
    order.append('space')
    adv['space'] = int(CAP * 0.30)

    chars = [ch for ch, _ in files]
    fb = FontBuilder(EM, isTTF=True)
    fb.setupGlyphOrder(order)
    cmap = {ord(ch): 'uni%04X' % ord(ch) for ch in chars if 'uni%04X' % ord(ch) in glyphs}
    cmap[0x20] = 'space'
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (adv[n], 0) for n in order})
    fb.setupHorizontalHeader(ascent=int(CAP * 1.2), descent=-int(CAP * 0.3))
    fb.setupNameTable({'familyName': 'HWLeica', 'styleName': 'Regular',
                       'uniqueFontIdentifier': 'HWLeica-Regular', 'fullName': 'HWLeica',
                       'psName': 'HWLeica-Regular', 'version': 'Version 6.0'})
    fb.setupOS2(sTypoAscender=int(CAP * 1.2), sTypoDescender=-int(CAP * 0.3),
                usWinAscent=int(CAP * 1.2), usWinDescent=int(CAP * 0.3))
    fb.setupPost()
    fb.save(OUT)
    print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB, glyphs', len(order) - 1)


if __name__ == '__main__':
    main()
