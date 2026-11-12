#!/usr/bin/env python3
"""把大写字母的高度统一到 700，基线对齐到 0。

各字体的现状：
- 常规体：M 750、V 734、Y 711，比其它大写高
- 细体粗版：整体只有 676（由常规粗体减细而来），M/V/Y 又特别高
- 手写体：逐字缩放导致 675–741 参差
"""
import os

from fontTools.ttLib import TTFont

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Bold.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Bold.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Bold.ttf",
]
CAP = 700.0
ROUND = set('OCSGQ')     # 圆字保留一点 overshoot
UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def main():
    for fp in FONTS:
        if not os.path.exists(fp):
            continue
        font = TTFont(fp)
        cmap = font.getBestCmap()
        glyf = font['glyf']
        changed = 0
        for ch in UPPER:
            if ord(ch) not in cmap:
                continue
            g = glyf[cmap[ord(ch)]]
            if getattr(g, 'numberOfContours', 0) <= 0:
                continue
            g.recalcBounds(glyf)
            h = g.yMax - g.yMin
            want = CAP + (4.0 if ch in ROUND else 0.0)
            if h <= 0 or abs(h - want) < 2:
                continue
            s = want / h
            g.coordinates.scale((s, s))
            g.recalcBounds(glyf)
            dy = -g.yMin
            if abs(dy) > 0.01:
                g.coordinates.translate((0, dy))
                g.recalcBounds(glyf)
            changed += 1
        font.save(fp)
        print(os.path.basename(fp), '调整', changed, '个大写', os.path.getsize(fp) // 1024, 'KB')


if __name__ == '__main__':
    main()
