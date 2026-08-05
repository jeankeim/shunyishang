"""
海报出图字体抽取与子集化脚本（阶段2 / Satori 用）
==================================================
Satori 渲染中文必须内嵌字体文件（TTF/OTF/WOFF）。全量 NotoSerifCJK
约 20MB，此脚本从系统字体集合（TTC）中抽取简体中文衬线字面，
并按 GB2312 + 常用符号子集化，产物约 1-3MB：

    apps/web/public/fonts/poster-serif.ttf  (或 .otf)

字体来源（按优先级）：
1. /usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc  (Debian fonts-noto-cjk)
2. /usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc
3. /System/Library/Fonts/Supplemental/Songti.ttc             (macOS 宋体)
4. /System/Library/Fonts/STHeiti Light.ttc                   (兜底黑体)

用法: python scripts/extract_poster_font.py [--force]
依赖: fonttools (pip install fonttools)
注意: 产物文件已 gitignore，Docker 构建时由 fonts 阶段自动生成。
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'apps' / 'web' / 'public' / 'fonts'

FONT_SOURCES = [
    '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc',
    '/System/Library/Fonts/Supplemental/Songti.ttc',
    '/System/Library/Fonts/STHeiti Light.ttc',
]


def build_charset() -> str:
    """GB2312 汉字 + 符号区 + ASCII + 常用标点"""
    chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
    chars |= set('·—…、。：；！？（）《》「」『』〈〉～％℃@#,.!?:&*+-/ ')
    # GB2312 符号区（1-9 区）
    for b1 in range(0xA1, 0xAA):
        for b2 in range(0xA1, 0xFF):
            try:
                chars.add(bytes([b1, b2]).decode('gb2312'))
            except Exception:
                pass
    # GB2312 汉字区（16-87 区）
    for b1 in range(0xB0, 0xF8):
        for b2 in range(0xA1, 0xFF):
            try:
                chars.add(bytes([b1, b2]).decode('gb2312'))
            except Exception:
                pass
    chars.discard('\x00')
    return ''.join(sorted(chars))


def pick_face(ttc_path: str):
    """从 TTC 中优先选择简体（SC）字面"""
    from fontTools.ttLib import TTCollection
    collection = TTCollection(ttc_path, lazy=True)
    for font in collection.fonts:
        family = font['name'].getDebugName(1) or ''
        if 'SC' in family.upper():
            return font
    return collection.fonts[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(OUT_DIR.glob('poster-serif.*'))
    if existing and not args.force:
        print(f'⏭  已存在，跳过: {existing[0]}')
        return 0

    source = next((p for p in FONT_SOURCES if Path(p).exists()), None)
    if not source:
        print('⚠️  未找到任何中文字体源，跳过生成（Satori 出图将降级到 Pillow）')
        return 0

    from fontTools.subset import Options, Subsetter
    print(f'📖 字体源: {source}')
    font = pick_face(source)
    family = font['name'].getDebugName(1)
    print(f'✂️  子集化字面: {family}（GB2312 + 常用符号）')

    options = Options()
    options.layout_features = []  # 海报无连字需求，进一步减小体积
    options.name_IDs = ['*']
    options.notdef_outline = True
    subsetter = Subsetter(options=options)
    subsetter.populate(text=build_charset())
    subsetter.subset(font)

    ext = 'otf' if font.sfntVersion == 'OTTO' else 'ttf'
    out_path = OUT_DIR / f'poster-serif.{ext}'
    font.save(str(out_path))
    print(f'✅ 生成: {out_path} ({out_path.stat().st_size / 1024:.0f} KB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
