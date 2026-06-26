"""倒放模块：反转 GIF 帧顺序，静态图原样返回"""

from PIL import Image
from .gif_utils import is_gif, unfold_frames, save_rgba_gif


def reverse_gif(input_path: str, output_path: str) -> str:
    """反转 GIF 帧顺序。静态图无动画帧，原样返回。"""
    gif = Image.open(input_path)

    if not is_gif(input_path):
        img = gif.convert("RGBA")
        img.save(output_path, "PNG")
        return output_path

    src_palette = gif.getpalette()
    src_trans = gif.info.get("transparency")
    frames, durations = unfold_frames(gif)

    frames.reverse()
    durations.reverse()

    save_rgba_gif(frames, durations, output_path, loop=gif.info.get("loop", 0),
                  source_palette=src_palette,
                  source_trans_idx=src_trans)
    return output_path
