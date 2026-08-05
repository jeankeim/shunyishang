"""
国风海报质感资产生成脚本（阶段1）
=================================
生成预烘焙质感资产到 data/standards/poster_assets/：

- paper_texture.png  宣纸纤维纹理（RGBA，低透明度斑点+纤维丝）
- ink_a.png          水墨晕染 A（左上+右下两团，白色墨形+alpha 形状）
- ink_b.png          水墨晕染 B（右上+左下两团）
- grain.png          纸面颗粒（灰度 L，渲染时加低透明度）
- seal_erosion.png   印章做旧蒙版（256x256 灰度，斑驳蚀刻）

渲染时用 ImageChops.multiply 将白色墨形染成主题色后叠加，
替代原 GaussianBlur 椭圆，获得真实水墨枯润边缘。

用法: python scripts/generate_poster_assets.py [--force]
依赖: Pillow, numpy
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'data' / 'standards' / 'poster_assets'

W, H = 1080, 1920
SEED = 20260802


def gen_paper_texture() -> Image.Image:
    """宣纸纤维纹理：细噪斑点 + 随机纤维丝，整体低透明度"""
    rng = np.random.default_rng(SEED)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))

    # 1) 细斑点：明暗两色噪点，alpha 极低
    n_dark = 26000
    pts = rng.integers(0, W, n_dark), rng.integers(0, H, n_dark)
    draw = ImageDraw.Draw(img)
    for x, y in zip(pts[0], pts[1]):
        gray = rng.integers(96, 150)
        draw.point((int(x), int(y)), fill=(int(gray), int(gray - 6), int(gray - 14), rng.integers(10, 26)))
    n_light = 18000
    pts = rng.integers(0, W, n_light), rng.integers(0, H, n_light)
    for x, y in zip(pts[0], pts[1]):
        draw.point((int(x), int(y)), fill=(252, 250, 242, rng.integers(12, 30)))

    # 2) 纤维丝：短曲线，近纸色，低透明
    for _ in range(420):
        x0 = rng.integers(0, W)
        y0 = rng.integers(0, H)
        angle = rng.uniform(0, np.pi)
        length = rng.integers(14, 64)
        x1 = int(x0 + np.cos(angle) * length)
        y1 = int(y0 + np.sin(angle) * length * 0.35)
        tone = int(rng.integers(176, 216))
        draw.line([(int(x0), int(y0)), (x1, y1)],
                  fill=(tone, tone - 8, tone - 20, int(rng.integers(8, 20))), width=1)

    return img


def _blob(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float,
          rng: np.random.Generator, alpha_peak: int):
    """绘制不规则墨团：半径抖动的多边形 + 重模糊，形成枯润边缘"""
    n_pts = 26
    pts = []
    for i in range(n_pts):
        ang = 2 * np.pi * i / n_pts
        rr = r * rng.uniform(0.62, 1.28)
        pts.append((cx + np.cos(ang) * rr, cy + np.sin(ang) * rr * rng.uniform(0.72, 1.0)))
    # 主墨团（白+alpha 峰值）
    draw.polygon(pts, fill=(255, 255, 255, alpha_peak))
    # 中心浓核
    core_r = r * rng.uniform(0.3, 0.45)
    draw.ellipse([cx - core_r, cy - core_r, cx + core_r, cy + core_r],
                 fill=(255, 255, 255, min(alpha_peak + 14, 64)))
    # 外围飞白溅点
    for _ in range(26):
        ang = rng.uniform(0, 2 * np.pi)
        dist = r * rng.uniform(1.02, 1.5)
        sx, sy = cx + np.cos(ang) * dist, cy + np.sin(ang) * dist
        sr = rng.uniform(1.5, 7)
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr],
                     fill=(255, 255, 255, int(rng.integers(8, 30))))


def gen_ink_sheet(blobs: list) -> Image.Image:
    """生成整幅水墨晕染层（白色墨形，alpha 编码浓淡，渲染时染色）"""
    rng = np.random.default_rng(SEED + 7)
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for cx, cy, r, peak in blobs:
        _blob(draw, cx, cy, r, rng, peak)
    # 重模糊让墨韵化开，再轻微锐化保留枯边
    layer = layer.filter(ImageFilter.GaussianBlur(46))
    return layer


def gen_grain() -> Image.Image:
    """纸面颗粒（灰度 L 模式，量化到 8 级利于压缩），渲染时统一加低透明度"""
    rng = np.random.default_rng(SEED + 13)
    hw, hh = W // 2, H // 2
    noise = rng.integers(0, 8, (hh, hw), dtype=np.uint8) * 32
    return Image.fromarray(noise, 'L').resize((W, H), Image.Resampling.BILINEAR)


def gen_seal_erosion(size: int = 256) -> Image.Image:
    """印章做旧蒙版：整体白底 + 随机蚀斑 + 边缘磨损（灰度 L）"""
    rng = np.random.default_rng(SEED + 21)
    arr = np.full((size, size), 255, dtype=np.uint8)
    # 蚀斑：大小不一的暗点簇
    for _ in range(340):
        cx, cy = rng.integers(4, size - 4, 2)
        r = rng.uniform(0.6, 3.4)
        yy, xx = np.ogrid[-cx:size - cx, -cy:size - cy]
        mask = xx * xx + yy * yy <= r * r
        arr[mask] = np.minimum(arr[mask], rng.integers(40, 150))
    # 边缘磨损：边框区域随机压暗
    edge = 10
    border = np.zeros((size, size), dtype=bool)
    border[:edge, :] = border[-edge:, :] = True
    border[:, :edge] = border[:, -edge:] = True
    wear = rng.uniform(0.55, 1.0, (size, size))
    arr[border] = (arr[border] * wear[border]).astype(np.uint8)
    img = Image.fromarray(arr, 'L')
    return img.filter(ImageFilter.GaussianBlur(0.6))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='已存在时强制重新生成')
    args = parser.parse_args()

    targets = {
        'paper_texture.png': gen_paper_texture,
        'ink_a.png': lambda: gen_ink_sheet([(120, 60, 400, 52), (980, 2020, 380, 30)]),
        'ink_b.png': lambda: gen_ink_sheet([(960, 40, 420, 44), (110, 2060, 360, 30)]),
        'grain.png': gen_grain,
        'seal_erosion.png': gen_seal_erosion,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, fn in targets.items():
        out = OUT_DIR / name
        if out.exists() and not args.force:
            print(f'⏭  已存在，跳过: {out}')
            continue
        img = fn()
        img.save(out, optimize=True)
        print(f'✅ 生成: {out} ({out.stat().st_size / 1024:.0f} KB)')

    print('\n全部资产就绪。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
