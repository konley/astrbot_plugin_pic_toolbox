"""哈哈镜模块：曲面镜扭曲效果（凸/凹/柱面/波浪/螺旋）"""

import cv2
import numpy as np
from PIL import Image
from .gif_utils import is_gif, unfold_frames, save_rgba_gif


def _make_maps(mirror_type, strength, h, w):
    """生成坐标映射图。返回 (map_x, map_y)，均为 float32。"""
    cx, cy = w / 2.0, h / 2.0
    max_r = min(cx, cy)

    y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = x_grid - cx
    dy = y_grid - cy

    if mirror_type == "bulge":
        r = np.sqrt(dx ** 2 + dy ** 2)
        r_norm = np.clip(r / max_r, 0, 1)
        power = 1.0 / (1.0 + 0.6 * strength)
        scale = np.where(r_norm > 1e-6, r_norm ** (power - 1), 1.0)
        map_x = cx + dx * scale
        map_y = cy + dy * scale

    elif mirror_type == "concave":
        r = np.sqrt(dx ** 2 + dy ** 2)
        r_norm = np.clip(r / max_r, 0, 1)
        power = 1.0 + 0.6 * strength
        scale = np.where(r_norm > 1e-6, r_norm ** (power - 1), 1.0)
        map_x = cx + dx * scale
        map_y = cy + dy * scale

    elif mirror_type == "cylinder_h":
        factor = 1.0 + strength * np.abs(dy) / max(cy, 1)
        map_x = cx + dx / factor
        map_y = y_grid

    elif mirror_type == "cylinder_v":
        factor = 1.0 + strength * np.abs(dx) / max(cx, 1)
        map_x = x_grid
        map_y = cy + dy / factor

    elif mirror_type == "wave":
        freq = 0.08
        amp = strength * 25
        map_x = x_grid + amp * np.sin(2 * np.pi * freq * y_grid)
        map_y = y_grid + amp * np.sin(2 * np.pi * freq * x_grid)

    elif mirror_type == "spiral":
        r = np.sqrt(dx ** 2 + dy ** 2)
        r_norm = np.clip(r / max_r, 0, 1)
        angle_offset = strength * np.pi * r_norm
        cos_a = np.cos(angle_offset)
        sin_a = np.sin(angle_offset)
        map_x = cx + dx * cos_a - dy * sin_a
        map_y = cy + dx * sin_a + dy * cos_a

    else:
        map_x = x_grid
        map_y = y_grid

    return map_x, map_y


def _apply_distortion(img_rgba, mirror_type, strength):
    """对单帧应用扭曲。"""
    arr = np.array(img_rgba)
    h, w = arr.shape[:2]
    map_x, map_y = _make_maps(mirror_type, strength, h, w)

    distorted = cv2.remap(arr, map_x, map_y, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REFLECT)
    return Image.fromarray(distorted)


def funhouse_mirror_image(input_path, output_path,
                          mirror_type="bulge", strength=1.0):
    """对图片/GIF 应用哈哈镜扭曲效果。

    Args:
        mirror_type: bulge / concave / cylinder_h / cylinder_v / wave / spiral
        strength: 扭曲强度 0.1~2.0
    """
    src = Image.open(input_path)
    if not is_gif(input_path):
        rgba = src.convert("RGBA")
        result = _apply_distortion(rgba, mirror_type, strength)
        result.save(output_path, "PNG")
        return

    frames, durations = unfold_frames(src)
    processed = [_apply_distortion(f, mirror_type, strength) for f in frames]
    save_rgba_gif(processed, durations, output_path,
                  loop=src.info.get("loop", 0))
