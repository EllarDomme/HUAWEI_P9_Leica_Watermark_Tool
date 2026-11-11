#!/usr/bin/env python3
"""用抠图重建字体（v7）：alpha 遮罩 → 补边 → 保角曲线拟合。

与之前失败版本的区别：
- 遮罩四周补 3px 黑边，避免轮廓贴着 crop 边界
- 复用 build_full3 的 vectorize（它在大字表上验证过，孔洞不会填实）
"""
import os
import sys
import glob

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_full3 import vectorize, CAP, EM, XH

SRC = r"E:\DeskTop\字符抠图高清版\chars"
OUT = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
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
    keep = keep[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return cv2.copyMakeBorder(keep, 3, 3, 3, 3, cv2.BORDER_CONSTANT, value=0)


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

    # 字高统计
    caps, xhs = [], []
    for ch, p in files:
        m = load_mask(p)
        if m is None:
            continue
        h = m.shape[0] - 6
        if ch.isupper() or ch.isdigit():
            caps.append(h)
        elif ch in 'aeomnrscuvwxz':
            xhs.append(h)
    cap_px = float(np.median(caps))
    xh_px = float(np.median(xhs)) if xhs else cap_px * 0.72
    print('cap', cap_px, 'x-height', xh_px)

    glyphs, order, adv = {}, ['.notdef'], {}
    pen = TTGlyphPen(None)
    glyphs['.notdef'] = pen.glyph()
    adv['.notdef'] = 500

    for ch, p in files:
        m = load_mask(p)
        if m is None:
            continue
        h = m.shape[0] - 6
        # 统一按大写字高缩放，小写自然就小，标点也不会被放大
        base = h + 3.0
        if ch in DESC:
            base = h - 0.21 * cap_px + 3.0
        cmds_list, ink_w = vectorize(m, cap_px, base, CAP)
        if not cmds_list:
            print('  empty', ch)
            continue

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

        name = 'uni%04X' % ord(ch)
        try:
            glyphs[name] = tpen.glyph()
        except Exception as e:
            print('  fail', ch, e)
            continue
        order.append(name)
        adv[name] = int(round(ink_w + CAP * GAP))

    tpen = TTGlyphPen(None)
    glyphs['space'] = tpen.glyph()
    order.append('space')
    adv['space'] = int(CAP * 0.30)

    chars = [c for c, _ in files]
    fb = FontBuilder(EM, isTTF=True)
    fb.setupGlyphOrder(order)
    cmap = {ord(c): 'uni%04X' % ord(c) for c in chars if 'uni%04X' % ord(c) in glyphs}
    cmap[0x20] = 'space'
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (adv[n], 0) for n in order})
    fb.setupHorizontalHeader(ascent=int(CAP * 1.2), descent=-int(CAP * 0.3))
    fb.setupNameTable({'familyName': 'HWLeica', 'styleName': 'Regular',
                       'uniqueFontIdentifier': 'HWLeica-Regular', 'fullName': 'HWLeica',
                       'psName': 'HWLeica-Regular', 'version': 'Version 7.0'})
    fb.setupOS2(sTypoAscender=int(CAP * 1.2), sTypoDescender=-int(CAP * 0.3),
                usWinAscent=int(CAP * 1.2), usWinDescent=int(CAP * 0.3))
    fb.setupPost()
    fb.save(OUT)
    print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB, glyphs', len(order) - 1)


if __name__ == '__main__':
    main()
