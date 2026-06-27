"""旋转模块：将图片转为旋转的圆形 GIF（默认顺时针），支持动图输入"""

from PIL import Image, ImageDraw
from .gif_utils import is_gif, unfold_frames, save_rgba_gif


def _make_circular_mask(size):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0] - 1, size[1] - 1), fill=255)
    return mask


def _crop_to_square_center(img):
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def _spin_frame(rgba, angle, size, circle_mask):
    """对单帧应用旋转 + 圆形裁切。"""
    square = _crop_to_square_center(rgba)
    if square.size[0] != size:
        square = square.resize((size, size))
    rotated = square.rotate(angle, expand=False, resample=Image.BICUBIC)
    r, g, b, a = rotated.split()
    a = Image.composite(a, Image.new("L", (size, size), 0), circle_mask)
    return Image.merge("RGBA", (r, g, b, a))


def spin_image(input_path, output_path,
               direction="clockwise",
               angle_step=6,
               frame_delay=40):
    """将图片/GIF 转为旋转的圆形 GIF。

    动图输入时，每帧按渐进角度旋转，原始动画与旋转叠加。
    """
    src = Image.open(input_path)
    n_spin = max(1, int(360 / abs(angle_step)))
    actual_step = 360.0 / n_spin
    if direction == "counterclockwise":
        actual_step = -actual_step

    if getattr(src, "is_animated", False):
        frames, durations = unfold_frames(src)
        n_src = len(frames)
        processed = []
        size = None
        circle_mask = None
        for i, f in enumerate(frames):
            rgba = f.convert("RGBA")
            if size is None:
                square = _crop_to_square_center(rgba)
                size = square.size[0]
                circle_mask = _make_circular_mask((size, size))
            angle = (360.0 / n_src) * i * (1 if direction == "clockwise" else -1)
            processed.append(_spin_frame(rgba, angle, size, circle_mask))
        save_rgba_gif(processed, durations, output_path, loop=0)
        return

    rgba = src.convert("RGBA")
    square = _crop_to_square_center(rgba)
    size = square.size[0]
    circle_mask = _make_circular_mask((size, size))

    frames = [_spin_frame(rgba, i * actual_step, size, circle_mask) for i in range(n_spin)]
    save_rgba_gif(frames, [frame_delay] * n_spin, output_path, loop=0)
