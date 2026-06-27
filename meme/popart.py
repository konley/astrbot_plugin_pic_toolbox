"""波普模块：安迪·沃霍尔风格（降色 + 描边 + 半调网点 + 多联画）"""

import math
import numpy as np
from PIL import Image, ImageDraw
from .gif_utils import is_gif, unfold_frames, save_rgba_gif


# 预设配色方案（每组 N 种颜色，用于多联画替换）
POP_PALETTES = [
    None,  # 0: 原色（不替换）
    [(255, 60, 60), (255, 220, 60), (60, 200, 60), (60, 180, 255), (180, 60, 255), (60, 60, 60)],   # 1: 波普暖
    [(60, 200, 255), (60, 60, 255), (200, 60, 255), (255, 60, 200), (60, 200, 200), (200, 200, 60)],  # 2: 波普冷
    [(255, 255, 255), (0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)],              # 3: 高对比
    [(255, 200, 0), (255, 100, 0), (200, 0, 0), (100, 0, 0), (50, 50, 50), (200, 200, 200)],         # 4: 暖橙
]


def _remap_colors(img_rgba, target_palette):
    """将量化后的图像颜色映射到目标调色板（最近邻）。"""
    arr = np.array(img_rgba.convert("RGBA"))
    h, w = arr.shape[:2]
    alpha = arr[:, :, 3]

    # 收集所有不重复的颜色
    rgb = arr[:, :, :3]
    flat = rgb.reshape(-1, 3)
    unique_colors = np.unique(flat, axis=0)

    # 对每种唯一颜色找到最近的目标色
    mapping = {}
    for uc in unique_colors:
        best_dist = float("inf")
        best_color = tuple(uc)
        for tc in target_palette:
            tc_arr = np.array(tc, dtype=np.int16)
            uc_arr = np.array(uc, dtype=np.int16)
            dist = np.sum((tc_arr - uc_arr) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_color = tc
        mapping[tuple(uc)] = best_color

    # 应用映射
    result = np.zeros_like(arr)
    for y in range(h):
        for x in range(w):
            c = tuple(rgb[y, x])
            result[y, x] = (*mapping[c], alpha[y, x])

    return Image.fromarray(result)


def _detect_edges(img_rgba, edge_width):
    """Canny 边缘检测 + 描黑边。"""
    import cv2
    arr = np.array(img_rgba.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    if edge_width > 1:
        kernel = np.ones((edge_width, edge_width), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

    # 在 rgba 上画黑边
    result = np.array(img_rgba.convert("RGBA"))
    result[edges > 0] = [0, 0, 0, 255]
    return Image.fromarray(result)


def _apply_halftone(img_rgba, dot_size):
    """半调网点效果。"""
    arr = np.array(img_rgba)
    h, w = arr.shape[:2]
    gray = Image.fromarray(arr).convert("L")
    result = np.array(img_rgba)

    for y in range(0, h, dot_size):
        for x in range(0, w, dot_size):
            block = gray.crop((x, y, min(x + dot_size, w), min(y + dot_size, h)))
            avg_bright = np.mean(np.array(block))
            # 亮度 → 点半径（暗=大点，亮=小点）
            radius = int((1 - avg_bright / 255) * dot_size / 2)
            radius = max(0, min(radius, dot_size // 2))
            cx, cy = x + dot_size // 2, y + dot_size // 2
            if radius > 0:
                color = tuple(int(arr[y, x, c]) for c in range(3))
                # 画实心圆
                cv2_color = (color[2], color[1], color[0])
                cv2.circle(result, (cx, cy), radius, cv2_color, -1)
            else:
                # 全亮区域：留白
                cv2.rectangle(result, (x, y), (min(x + dot_size, w), min(y + dot_size, h)), (255, 255, 255, 255), -1)

    return Image.fromarray(result)


def popart_image(input_path, output_path,
                 num_colors=6, edge_width=3,
                 halftone_size=0, panels=1):
    """生成波普艺术风格图片。

    Args:
        num_colors: 颜色数（2~8）
        edge_width: 描边宽度（0=不描边）
        halftone_size: 网点大小（0=不启用）
        panels: 多联画格数（1/2/4）
    """
    src = Image.open(input_path)
    if getattr(src, "is_animated", False):
        src.seek(0)
    rgba = src.convert("RGBA")

    if panels > 1:
        # 多联画：取首帧，切成几份不同配色
        side = min(rgba.size)
        cx, cy = rgba.size[0] // 2, rgba.size[1] // 2
        square = rgba.crop((cx - side // 2, cy - side // 2,
                            cx + side // 2, cy + side // 2))

        # 量化到 N 色
        rgb = square.convert("RGB")
        quantized = rgb.quantize(colors=num_colors, method=Image.Quantize.FASTOCTREE)
        base = quantized.convert("RGBA")
        # 描边
        if edge_width > 0:
            base = _detect_edges(base, edge_width)
        # 半调
        if halftone_size > 0:
            base = _apply_halftone(base, halftone_size)

        # 生成各面板
        psize = side
        panels_per_row = 2 if panels <= 4 else 3
        rows = (panels + panels_per_row - 1) // panels_per_row
        cols = min(panels, panels_per_row)
        canvas = Image.new("RGBA", (psize * cols, psize * rows), (255, 255, 255, 255))

        for i in range(panels):
            palette_idx = i % len(POP_PALETTES)
            if palette_idx == 0 or POP_PALETTES[palette_idx] is None:
                panel = base.copy()
            else:
                panel = _remap_colors(base, POP_PALETTES[palette_idx])
                if edge_width > 0:
                    # 重描边（颜色映射后边可能被覆盖）
                    panel = _detect_edges(panel, edge_width)
            px = (i % cols) * psize
            py = (i // cols) * psize
            canvas.paste(panel, (px, py))

        canvas.save(output_path, "PNG")
        return

    # ── 单图模式（支持 GIF） ──
    if not is_gif(input_path):
        rgb = rgba.convert("RGB")
        quantized = rgb.quantize(colors=num_colors, method=Image.Quantize.FASTOCTREE)
        result = quantized.convert("RGBA")
        if edge_width > 0:
            result = _detect_edges(result, edge_width)
        if halftone_size > 0:
            result = _apply_halftone(result, halftone_size)
        result.save(output_path, "PNG")
        return

    # GIF
    src_palette = src.getpalette()
    src_trans = src.info.get("transparency")
    frames, durations = unfold_frames(src)
    processed = []
    for f in frames:
        rgb = f.convert("RGB")
        q = rgb.quantize(colors=num_colors, method=Image.Quantize.FASTOCTREE)
        result = q.convert("RGBA")
        if edge_width > 0:
            result = _detect_edges(result, edge_width)
        if halftone_size > 0:
            result = _apply_halftone(result, halftone_size)
        processed.append(result)

    save_rgba_gif(processed, durations, output_path,
                  loop=src.info.get("loop", 0))
