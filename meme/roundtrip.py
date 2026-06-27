"""往返模块：GIF 正序 + 倒序拼接，形成 ping-pong 循环"""

from PIL import Image
from .gif_utils import is_gif, unfold_frames, save_rgba_gif


def roundtrip_gif(input_path: str, output_path: str):
    """GIF 往返效果：正序播放结束后倒序播放再拼接。"""
    gif = Image.open(input_path)

    if not is_gif(input_path):
        img = gif.convert("RGBA")
        img.save(output_path, "PNG")
        return

    src_palette = gif.getpalette()
    src_trans = gif.info.get("transparency")
    frames, durations = unfold_frames(gif)

    if len(frames) <= 1:
        save_rgba_gif(frames, durations, output_path, loop=gif.info.get("loop", 0),
                      source_palette=src_palette,
                      source_trans_idx=src_trans)
        return

    # 正序 + 倒序（去掉首尾帧避免重复）
    rev_frames = frames[-2:0:-1]
    rev_durations = durations[-2:0:-1]

    combined_frames = frames + rev_frames
    combined_durations = durations + rev_durations

    save_rgba_gif(combined_frames, combined_durations, output_path,
                  loop=gif.info.get("loop", 0),
                  source_palette=src_palette,
                  source_trans_idx=src_trans)
