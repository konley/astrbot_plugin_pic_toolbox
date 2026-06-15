"""GIF 速度调控：0.3x ~ 5.0x 变速，支持 50 FPS 上限回退与均匀丢帧"""

from PIL import Image
from .gif_utils import unfold_frames, save_kwargs_for

_GIF_MIN_DURATION_MS = 20       # 业务上限：帧间隔不低于 20ms（→ 最高 50 FPS）
_GIF_MAX_FPS = 1000 // _GIF_MIN_DURATION_MS  # 50


def parse_speed(s: str) -> float:
    try:
        v = round(float(s), 1)
    except (ValueError, TypeError):
        raise ValueError(f"无效的速度值: {s}")
    if v < 0.3 or v > 5.0:
        raise ValueError(f"速度范围 0.3 ~ 5.0，收到: {v}")
    return v


def adjust_gif_speed(
    input_path: str,
    output_path: str,
    speed: float,
    allow_frame_drop: bool = False,
) -> tuple:
    """调速 GIF，返回 (output_path, actual_speed, warning_msg_or_None)。

    - speed: 目标倍率（0.3 ~ 5.0）
    - allow_frame_drop: 当倍率使帧率超过 50 FPS 时，是否允许通过均匀丢帧
      来实现目标倍率（默认 False 时自动回退到最高不超过 50 FPS 的倍率）。
    """
    gif = Image.open(input_path)
    frames, durations = unfold_frames(gif)

    frame_count = len(frames)
    if frame_count == 0:
        frames[0].save(output_path, "GIF")
        return output_path, speed, None

    total_dur_ms = sum(durations)
    if total_dur_ms <= 0:
        total_dur_ms = frame_count * 100  # 假设默认 100ms/帧

    # 原始平均 FPS
    original_avg_fps = frame_count * 1000.0 / total_dur_ms
    # 调速后的目标 FPS
    target_fps = original_avg_fps * speed

    # ── 情况 1：目标 FPS 在 100 以内，直接调速 ──
    if target_fps <= _GIF_MAX_FPS:
        new_durs = [max(_GIF_MIN_DURATION_MS, min(65535, int(d / speed))) for d in durations]
        kwargs = save_kwargs_for(gif, new_durs)
        kwargs.update(save_all=True, append_images=frames[1:] if frame_count > 1 else [])
        frames[0].save(output_path, "GIF", **kwargs)
        return output_path, speed, None

    # ── 情况 2：不允许丢帧 → 回退到不超过 100 FPS 的最高倍率 ──
    if not allow_frame_drop:
        max_multiplier = _GIF_MAX_FPS / original_avg_fps
        max_multiplier = round(max_multiplier * 10) / 10  # 保留 1 位小数
        if max_multiplier > 5.0:
            max_multiplier = 5.0
        if max_multiplier < 0.3:
            max_multiplier = 0.3

        actual_fps = original_avg_fps * max_multiplier if max_multiplier >= 0.3 else original_avg_fps * 0.3
        new_durs = [max(_GIF_MIN_DURATION_MS, min(65535, int(d / max_multiplier))) for d in durations]
        kwargs = save_kwargs_for(gif, new_durs)
        kwargs.update(save_all=True, append_images=frames[1:] if frame_count > 1 else [])
        frames[0].save(output_path, "GIF", **kwargs)

        warning = (
            f"⚠️ GIF 调速提醒：原 GIF {original_avg_fps:.1f} FPS，"
            f"×{speed} 后帧率将达 {target_fps:.0f} FPS，"
            f"超出 50 FPS 上限。\n"
            f"已自动回退至 ×{max_multiplier}（≈ {actual_fps:.0f} FPS）。"
        )
        return output_path, max_multiplier, warning

    # ── 情况 3：允许丢帧 → 均匀丢弃帧使单帧时长 ≥ 10ms ──
    # 每 keep_every 帧保留 1 帧，丢弃其余
    # 需满足: 保留帧数 × 10ms ≤ 原总时长 / speed
    target_total_ms = total_dur_ms / speed
    max_keepable = int(target_total_ms / _GIF_MIN_DURATION_MS)
    if max_keepable < 1:
        max_keepable = 1
    keep_every = max(1, (frame_count + max_keepable - 1) // max_keepable)  # ceil division

    kept_frames = frames[::keep_every]
    kept_durations = durations[::keep_every]

    new_durs = [max(_GIF_MIN_DURATION_MS, min(65535, int(d / speed))) for d in kept_durations]
    kwargs = save_kwargs_for(gif, new_durs)
    kwargs.update(save_all=True, append_images=kept_frames[1:] if len(kept_frames) > 1 else [])
    kept_frames[0].save(output_path, "GIF", **kwargs)

    # 计算实际达到的帧率
    actual_total = sum(new_durs)
    actual_fps = len(kept_frames) * 1000.0 / actual_total if actual_total > 0 else 100
    warning = (
        f"ℹ️ GIF 调速：原 {frame_count} 帧 / {original_avg_fps:.1f} FPS，"
        f"已通过均匀丢帧（保留 {len(kept_frames)} 帧，每 {keep_every} 取 1）"
        f"加速至 ×{speed}，当前约 {actual_fps:.0f} FPS。"
    )

    return output_path, speed, warning
