#!/usr/bin/env python3
"""扩充 kerning：按类别生成 100+ 组字距对。

覆盖：
- 斜边字（A V W Y）与开放字（o e a c s u y）、标点、数字
- T / L / P / F 与后续字母
- 数字与单位（mm、f/、2.8、1/250s、ISO）
- 标点组合（. , : ; / -）
"""
import os

from fontTools.ttLib import TTFont
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

SRC = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
DST = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"

DIAG = 'AVWY'
FLAT = 'HIJLN'
OPEN = 'o e a c s u y d q g b p'
PUNCT = '.,:;-'
DIGITS = '0123456789'
LOWER = 'acemnorsuvwxz'

PAIRS = []


def add(lefts, rights, value):
    for a in lefts.replace(' ', ''):
        for b in rights.replace(' ', ''):
            PAIRS.append((a, b, value))


# 斜边字
add(DIAG, OPEN, -32)
add(DIAG, PUNCT, -65)
add(DIAG, DIGITS, -12)
add(DIAG, DIAG, -20)

# T
add('T', OPEN, -26)
add('T', PUNCT, -55)
add('T', DIAG, -35)
add('T', 'r', -20)

# L
add('L', 'TVWY', -42)
add('L', OPEN, -12)
add('L', 'TJ', -20)

# P F
add('PF', OPEN, -22)
add('PF', PUNCT, -45)
add('PF', DIAG, -30)

# Y 后接
add('Y', 'aeiou', -30)

# 数字与单位
PAIRS += [('3', '5', -6), ('5', 'm', -8), ('m', 'm', -14), ('m', 'f', -12),
          ('f', '/', -14), ('/', '2', -22), ('2', '.', -10),
          ('.', '8', -12), ('8', 'I', -8), ('I', 'S', -14), ('S', 'O', -16),
          ('1', '/', -8), ('5', '0', -8), ('0', 's', -10),
          ('s', 'I', -12), ('0', '0', -8), ('1', '0', -10), ('4', '0', -8)]

# 标点
add('.', DIGITS, -12)
add(',', DIGITS, -12)
add(':', DIGITS, -12)
add('-', DIGITS, -8)
add('r', '.,:;', -28)
add('f', '.,:;', -20)
add('a', 'cdeogq', -8)
add('e', 'acdeogq', -6)

# 小写常见
for a, b, v in [('l', 'l', -12), ('i', 'l', -10), ('t', 'o', -10),
                ('r', 'a', -12), ('r', 'o', -12), ('v', 'o', -8),
                ('w', 'o', -8), ('y', 'o', -8), ('k', 'e', -8)]:
    PAIRS.append((a, b, v))


def main():
    font = TTFont(SRC)
    cmap = font.getBestCmap()

    # 空格稍加宽，避免数字与单位粘在一起
    if 'space' in font['hmtx'].metrics:
        font['hmtx']['space'] = (260, 0)

    # 清掉旧 GPOS，避免重复
    for t in ('GPOS', 'GDEF'):
        if t in font:
            del font[t]

    seen = set()
    lines = ['feature kern {']
    count = 0
    for a, b, v in PAIRS:
        na = cmap.get(ord(a))
        nb = cmap.get(ord(b))
        # 名字里用符号的，转成 uniXXXX / 单词名
        if na is None or nb is None:
            continue
        key = (na, nb)
        if key in seen:
            continue
        seen.add(key)
        lines.append('  pos \\%s \\%s %d;' % (na, nb, v))
        count += 1
    lines.append('} kern;')

    try:
        addOpenTypeFeaturesFromString(font, '\n'.join(lines))
    except Exception as e:
        print('compile failed:', e)
        return

    font.save(DST)
    print('kern pairs:', count, '| saved', os.path.getsize(DST) // 1024, 'KB')


if __name__ == '__main__':
    main()
