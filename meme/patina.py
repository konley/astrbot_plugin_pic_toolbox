"""包浆模块：复古做旧效果（染色 + 暗角 + 噪点 + 褪色）"""

import random
from PIL import Image, ImageFilter
from .gif_utils import is_gif, unfold_frames, save_rgba_gif


def _sepia_tone(img, strength):
    """叠加暖黄 Sepia 色调。strength: 0-100。"""
    r, g, b, a = img.split()
    # 标准 Sepia 矩阵
    sr = r.copy().point(lambda p: min(255, int(p * 0.393 + 0)))
    sg = g.copy().point(lambda p: min(255, int(p * 0.769 + 0)))
    sb = b.copy().point(lambda p: min(255, int(p * 0.189 + 0)))
    sepia = Image.merge("RGBA", (sr, sg, sb, a))

    blend_factor = strength / 100.0
    return Image.blend(img, sepia, blend_factor)


def _vignette(img, strength):
    """边缘暗角。strength: 0-100。"""
    w, h = img.size
    cx, cy = w / 2, h / 2
    max_r = max(cx, cy)

    # 径向渐层蒙版
    import math
    mask = Image.new("L", (w, h), 255)
    for y in range(h):
        for x in range(w):
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            factor = 1 - (d / max_r) * (strength / 100.0)
            factor = max(0, min(1, factor))
            mask.putpixel((x, y), int(255 * factor))

    r, g, b, a = img.split()
    r = Image.composite(r, Image.new("L", (w, h), 0), mask)
    g = Image.composite(g, Image.new("L", (w, h), 0), mask)
    b = Image.composite(b, Image.new("L", (w, h), 0), mask)
    return Image.merge("RGBA", (r, g, b, a))


def _add_noise(img, amount):
    """添加颗粒噪点。amount: 0-100。"""
    import numpy as np
    arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-amount, amount + 1, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _fade(img, amount):
    """褪色：降饱和 + 降对比 + 加白雾。amount: 0-100。"""
    # 降低饱和度
    r, g, b, a = img.split()
    gray = Image.composite(
        Image.merge("RGBA", (r, g, b, a)).convert("L").convert("RGBA"),
        Image.new("RGBA", img.size, (0, 0, 0, 0)), a
    )
    gray_r, gray_g, gray_b, gray_a = gray.split()
    f = amount / 100.0
    r = Image.blend(r, gray_r, f * 0.5)
    g = Image.blend(g, gray_g, f * 0.5)
    b = Image.blend(b, gray_b, f * 0.5)

    # 加白雾
    white = Image.new("RGBA", img.size, (255, 255, 255, 0))
    result = Image.merge("RGBA", (r, g, b, a))
    result = Image.blend(result, white, f * 0.3)
    return result


def patina_image(input_path, output_path,
                 sepia_strength=60, vignette_strength=40,
                 noise_amount=20, fade_amount=30):
    """对图片/GIF 应用复古做旧效果。"""
    src = Image.open(input_path)
    if not is_gif(input_path):
        rgba = src.convert("RGBA")
        rgba = _sepia_tone(rgba, sepia_strength)
        rgba = _fade(rgba, fade_amount)
        rgba = _vignette(rgba, vignette_strength)
        rgba = _add_noise(rgba, noise_amount)
        rgba.save(output_path, "PNG")
        return

    src_palette = src.getpalette()
    src_trans = src.info.get("transparency")
    frames, durations = unfold_frames(src)

    processed = []
    for f in frames:
        f = _sepia_tone(f, sepia_strength)
        f = _fade(f, fade_amount)
        f = _vignette(f, vignette_strength)
        f = _add_noise(f, noise_amount)
        processed.append(f)

    save_rgba_gif(processed, durations, output_path,
                  loop=src.info.get("loop", 0))
