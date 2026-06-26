"""马赛克模块：静态图/GIF 马赛克马赛克处理"""

from PIL import Image
from .gif_utils import is_gif, unfold_frames, save_rgba_gif


def _pixelate_frame(img: Image.Image, block_size: int) -> Image.Image:
    """对单帧执行马赛克：缩小后用最近邻放大，产生马赛克效果。"""
    w, h = img.size
    small_w = max(1, w // block_size)
    small_h = max(1, h // block_size)
    small = img.resize((small_w, small_h), Image.BILINEAR)
    return small.resize((w, h), Image.NEAREST)


def pixelate_image(input_path: str, output_path: str, block_size: int = 8) -> str:
    """马赛克处理。

    block_size: 像素块边长（2~50），值越大马赛克越明显。
    """
    block_size = max(2, min(50, int(block_size)))
    gif = Image.open(input_path)

    if not is_gif(input_path):
        img = gif.convert("RGBA")
        _pixelate_frame(img, block_size).save(output_path, "PNG")
        return output_path

    src_palette = gif.getpalette()
    src_trans = gif.info.get("transparency")
    frames, durations = unfold_frames(gif)
    pixelated = [_pixelate_frame(f, block_size) for f in frames]

    save_rgba_gif(pixelated, durations, output_path, loop=gif.info.get("loop", 0),
                  source_palette=src_palette,
                  source_trans_idx=src_trans)
    return output_path
