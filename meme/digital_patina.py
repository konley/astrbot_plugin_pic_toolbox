"""电子包浆模块：模拟互联网图片反复蹂躏效果（JPEG 伪影 + 色彩断层 + 像素化 + 绿色偏色）"""

import io
import numpy as np
from PIL import Image
from .gif_utils import is_gif, unfold_frames, save_rgba_gif


def _jpeg_artifacts(img_rgba, quality):
    """重压 JPEG 引入块状伪影。quality: 1-100，越低越严重。"""
    buf = io.BytesIO()
    white = Image.new("RGB", img_rgba.size, (255, 255, 255))
    white.paste(img_rgba, mask=img_rgba.split()[3])
    white.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    degraded = Image.open(buf).convert("RGBA")
    _, _, _, orig_a = img_rgba.split()
    r, g, b, _ = degraded.split()
    return Image.merge("RGBA", (r, g, b, orig_a))


def _color_banding(img_rgba, levels):
    """色彩断层：将每个通道降为 N 个色阶。levels: 2-256，越小断层越明显。"""
    arr = np.array(img_rgba, dtype=np.uint8)
    step = 256 // levels
    banded = (arr.astype(np.int16) // step) * step + step // 2
    banded = np.clip(banded, 0, 255).astype(np.uint8)
    return Image.fromarray(banded)


def _pixelate_image(img_rgba, block_size):
    """像素化。block_size: 2-50，越大越糊。"""
    w, h = img_rgba.size
    sm = img_rgba.resize((max(1, w // block_size), max(1, h // block_size)), Image.NEAREST)
    return sm.resize((w, h), Image.NEAREST)


def _green_tint(img_rgba, strength):
    """偏绿色调。strength: 0-100，越大越绿。"""
    arr = np.array(img_rgba, dtype=np.int16)
    f = strength / 100.0
    # 红蓝衰减，绿色增强
    arr[:, :, 0] = np.clip(arr[:, :, 0] * (1 - f * 0.6), 0, 255).astype(np.uint8)
    arr[:, :, 2] = np.clip(arr[:, :, 2] * (1 - f * 0.6), 0, 255).astype(np.uint8)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + (255 - arr[:, :, 1]) * f * 0.4, 0, 255).astype(np.uint8)
    return Image.fromarray(arr.astype(np.uint8))


def digital_patina_image(input_path, output_path,
                         jpeg_quality=15, banding_level=5,
                         pixelate_size=0, green_tint=40):
    """对图片/GIF 应用电子包浆效果。"""
    src = Image.open(input_path)
    if not is_gif(input_path):
        rgba = src.convert("RGBA")
        rgba = _jpeg_artifacts(rgba, jpeg_quality)
        rgba = _color_banding(rgba, banding_level)
        if pixelate_size > 0:
            rgba = _pixelate_image(rgba, pixelate_size)
        rgba = _green_tint(rgba, green_tint)
        rgba.save(output_path, "PNG")
        return

    frames, durations = unfold_frames(src)
    processed = []
    for f in frames:
        f = _jpeg_artifacts(f, jpeg_quality)
        f = _color_banding(f, banding_level)
        if pixelate_size > 0:
            f = _pixelate_image(f, pixelate_size)
        f = _green_tint(f, green_tint)
        processed.append(f)

    save_rgba_gif(processed, durations, output_path,
                  loop=src.info.get("loop", 0))
