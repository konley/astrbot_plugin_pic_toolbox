"""故障模块：RGB 通道分离偏移，生成赛博故障风 GIF，支持动图输入"""

import random
from PIL import Image, ImageChops
from .gif_utils import is_gif, unfold_frames, save_rgba_gif


def _glitch_frame(rgba, max_shift):
    """对单帧应用随机 RGB 通道偏移。"""
    r, g, b, a = rgba.split()
    w, h = rgba.size
    shift_rx = random.randint(-max_shift, max_shift)
    shift_ry = random.randint(-max_shift // 2, max_shift // 2)
    shift_bx = random.randint(-max_shift, max_shift)
    shift_by = random.randint(-max_shift // 2, max_shift // 2)
    r_s = ImageChops.offset(r, shift_rx, shift_ry).crop((0, 0, w, h))
    b_s = ImageChops.offset(b, shift_bx, shift_by).crop((0, 0, w, h))
    return Image.merge("RGBA", (r_s, g, b_s, a))


def glitch_image(input_path, output_path, max_shift=15, num_frames=8, frame_delay=80):
    """RGB 通道随机偏移，生成故障风 GIF。动图输入时逐帧故障。"""
    src = Image.open(input_path)
    if getattr(src, "is_animated", False):
        frames, durations = unfold_frames(src)
        processed = [_glitch_frame(f.convert("RGBA"), max_shift) for f in frames]
        save_rgba_gif(processed, durations, output_path, loop=0)
        return

    rgba = src.convert("RGBA")
    frames = [_glitch_frame(rgba, max_shift) for _ in range(num_frames)]
    save_rgba_gif(frames, [frame_delay] * num_frames, output_path, loop=0)
