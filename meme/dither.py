"""抖动模块：降色阶 + 误差扩散抖动，复古 8-bit 风"""

from PIL import Image
from .gif_utils import is_gif, unfold_frames, save_rgba_gif


def dither_image(input_path, output_path, num_colors=16):
    """将图片/GIF 降色阶 + 抖动，模拟复古 8-bit 风格。

    Args:
        num_colors: 颜色数（2~256），越小越复古，2=纯黑白
    """
    src = Image.open(input_path)
    n_colors = max(2, min(256, num_colors))

    if not is_gif(input_path):
        rgba = src.convert("RGBA")
        rgb = rgba.convert("RGB")
        quantized = rgb.quantize(colors=n_colors, method=Image.Quantize.FASTOCTREE,
                                 dither=Image.Dither.FLOYDSTEINBERG)
        result = quantized.convert("RGBA")
        # 恢复原始透明
        r, g, b, a = result.split()
        _, _, _, src_a = rgba.split()
        result = Image.merge("RGBA", (r, g, b, src_a))
        result.save(output_path, "PNG")
        return

    src_palette = src.getpalette()
    src_trans = src.info.get("transparency")
    frames, durations = unfold_frames(src)

    processed = []
    for f in frames:
        rgb = f.convert("RGB")
        q = rgb.quantize(colors=n_colors, method=Image.Quantize.FASTOCTREE,
                         dither=Image.Dither.FLOYDSTEINBERG)
        rgba_q = q.convert("RGBA")
        fr, fg, fb, _ = rgba_q.split()
        _, _, _, fa = f.convert("RGBA").split()
        processed.append(Image.merge("RGBA", (fr, fg, fb, fa)))

    save_rgba_gif(processed, durations, output_path,
                  loop=src.info.get("loop", 0))
