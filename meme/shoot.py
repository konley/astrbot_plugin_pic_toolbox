"""Shoot meme: 射击表情包 — 13帧 GIF，支持正面+侧脸检测"""

import os
import numpy as np
from PIL import Image

_FRAMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resource", "shoot_frames")
_FRAME_COUNT = 13
_DURATION = 150

_cascade = None
_profile_cascade = None


def _get_cascade():
    global _cascade, _profile_cascade
    if _cascade is None:
        import cv2
        _cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        _profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    return _cascade, _profile_cascade


def _detect_face_focal(img: Image.Image):
    try:
        fc, pc = _get_cascade()
        gray = np.array(img.convert("L"))
        for cascade in (fc, pc):
            for sf, mn in ((1.05, 3), (1.01, 2)):
                faces = cascade.detectMultiScale(gray, scaleFactor=sf, minNeighbors=mn, minSize=(30, 30))
                if len(faces):
                    x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
                    return (x + w // 2, y + h // 2)
        return None
    except Exception:
        return None


def _resize_cover(img: Image.Image, target: tuple[int, int], focal=None):
    tw, th = target
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    new_w, new_h = int(iw * scale), int(ih * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)

    if focal:
        fx, fy = focal[0] * scale, focal[1] * scale
        left, top = int(fx - tw / 2), int(fy - th / 2)
    else:
        left, top = (new_w - tw) // 2, (new_h - th) // 2

    left = max(0, min(left, new_w - tw))
    top = max(0, min(top, new_h - th))
    return resized.crop((left, top, left + tw, top + th))


def generate_shoot(input_path: str, output_path: str) -> str:
    avatar = Image.open(input_path).convert("RGBA")
    focal = _detect_face_focal(avatar)
    frames = []

    for i in range(_FRAME_COUNT):
        overlay = Image.open(os.path.join(_FRAMES_DIR, f"{i:02d}.png")).convert("RGBA")
        base = _resize_cover(avatar, overlay.size, focal)
        base.paste(overlay, (0, 0), overlay)
        frames.append(base)

    frames[0].save(
        output_path, "GIF", save_all=True, append_images=frames[1:],
        duration=_DURATION, loop=0, disposal=2,
    )
    return output_path
