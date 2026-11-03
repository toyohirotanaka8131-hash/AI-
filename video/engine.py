"""「知らなかった！野菜と果物のヒミツ」シリーズ共通の動画エンジン。

- 縦型 1080x1920 / 30fps
- 案内役：柴犬「コロ」（吹き出し・口パク・ジャンプ）
- 声：Open JTalk + 東北大学 HTS voice tohoku-f01（happy, CC BY 4.0）
- BGM・効果音は numpy で合成

各動画は Scene のリストを作って Video(...).render() を呼ぶだけ。
シーンの長さはセリフの長さに合わせて自動で延びる（セリフが切れない）。
"""
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"

JTALK_DIC = "/var/lib/mecab/dic/open-jtalk/naist-jdic"
JTALK_VOICE = os.path.join(HERE, "voices", "tohoku-f01-happy.htsvoice")
VOICE_PITCH = 2
VOICE_SPEED = 1.0
VOICE_INTONATION = 1.25

SERIES = "知らなかった！野菜と果物のヒミツ"


# ================================================================ utilities
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, start, dur):
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 3 * x * x - 2 * x * x * x


def ease_out_back(x, s=1.9):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def with_alpha(img, a):
    if a >= 1:
        return img
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return img


def paste_center(frame, img, cx, cy, alpha=1.0):
    if alpha <= 0 or img.width == 0 or img.height == 0:
        return
    frame.alpha_composite(with_alpha(img, alpha), (int(cx - img.width / 2), int(cy - img.height / 2)))


def scaled(img, s, sy=None):
    sy = s if sy is None else sy
    if abs(s - 1.0) < 1e-3 and abs(sy - 1.0) < 1e-3:
        return img
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * sy))), Image.BILINEAR)


def rotated(img, deg):
    return img.rotate(deg, resample=Image.BICUBIC, expand=True) if abs(deg) > 0.05 else img


_font_cache = {}


def font(size):
    if size not in _font_cache:
        _font_cache[size] = ImageFont.truetype(FONT_PATH, size)
    return _font_cache[size]


_text_cache = {}


def text_img(text, size, fill=(255, 255, 255), stroke=0, stroke_fill=(0, 0, 0), spacing=14):
    key = (text, size, fill, stroke, stroke_fill)
    if key in _text_cache:
        return _text_cache[key]
    f = font(size)
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    box = dummy.multiline_textbbox((0, 0), text, font=f, stroke_width=stroke, spacing=spacing, align="center")
    w, h = int(math.ceil(box[2] - box[0])) + 8, int(math.ceil(box[3] - box[1])) + 8
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).multiline_text((4 - box[0], 4 - box[1]), text, font=f, fill=fill, stroke_width=stroke,
                                       stroke_fill=stroke_fill, spacing=spacing, align="center")
    _text_cache[key] = img
    return img


def label(text, size=64, fill=(255, 255, 255), stroke_fill=(190, 60, 0), stroke=10):
    return text_img(text, size, fill=fill, stroke=stroke, stroke_fill=stroke_fill)


def sprite(w, h, fn, ss=2):
    """w x h のRGBAスプライトを ss 倍で描いて縮小する（なめらかな輪郭）。fn(draw, k) の k は倍率。"""
    img = Image.new("RGBA", (int(w * ss), int(h * ss)), (0, 0, 0, 0))
    fn(ImageDraw.Draw(img), ss, img)
    return img.resize((int(w), int(h)), Image.LANCZOS)


def ball(size, light_c, base_c, dark_c, squash=1.0, light=(-0.35, -0.42), spec=0.55):
    """光が当たった球（果物の基本形）。"""
    n = int(size)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    nx = (xx - n / 2) / (n / 2)
    ny = (yy - n / 2) / (n / 2 * squash)
    r = np.sqrt(nx ** 2 + ny ** 2)
    dl = np.sqrt((nx - light[0]) ** 2 + (ny - light[1]) ** 2)
    t = np.clip(dl / 1.25, 0, 1)[..., None]
    col = np.array(light_c, float) * (1 - t) + np.array(base_c, float) * t
    edge = np.clip((r - 0.75) / 0.25, 0, 1)[..., None] ** 1.5
    col = col * (1 - 0.55 * edge) + np.array(dark_c, float) * 0.55 * edge
    sp = np.exp(-(dl ** 2) / 0.018)[..., None]
    col = col * (1 - spec * sp) + 255 * spec * sp
    alpha = np.clip((1.0 - r) * n / 3, 0, 1) * 255
    out = np.zeros((n, n, 4), np.uint8)
    out[..., :3] = col.clip(0, 255)
    out[..., 3] = alpha.astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def soft_shadow(w, h, alpha=90):
    img = Image.new("RGBA", (int(w) + 80, int(h) + 80), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((40, 40, 40 + w, 40 + h), fill=(150, 80, 20, alpha))
    return img.filter(ImageFilter.GaussianBlur(18))


def make_sparkle(size, color=(255, 255, 255)):
    def fn(d, k, _):
        c = size * k / 2
        pts = []
        for i in range(8):
            a = i * math.pi / 4
            rr = c if i % 2 == 0 else c * 0.24
            pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
        d.polygon(pts, fill=color + (255,))
    return sprite(size, size, fn)


SPARKLE_W = None
SPARKLE_Y = None


def draw_sparkles(frame, t, cx, cy, radius, seed, n=6):
    global SPARKLE_W, SPARKLE_Y
    if SPARKLE_W is None:
        SPARKLE_W, SPARKLE_Y = make_sparkle(90), make_sparkle(70, (255, 236, 150))
    rng = random.Random(seed)
    for i in range(n):
        ph, per = rng.uniform(0, 1), rng.uniform(0.9, 1.4)
        s = math.sin(((t / per + ph) % 1.0) * math.pi)
        ang = rng.uniform(0, 2 * math.pi)
        rr = radius * rng.uniform(0.9, 1.25)
        spr = SPARKLE_W if i % 2 else SPARKLE_Y
        paste_center(frame, scaled(spr, 0.3 + 0.7 * s), cx + math.cos(ang) * rr, cy + math.sin(ang) * rr, alpha=s)


def make_bookmark(size):
    def fn(d, k, img):
        w, h = img.size
        pts = [(5 * k, 5 * k), (w - 5 * k, 5 * k), (w - 5 * k, h - 5 * k), (w / 2, h * 0.7), (5 * k, h - 5 * k)]
        d.polygon(pts, fill=(255, 255, 255, 255))
        d.line(pts + [pts[0]], fill=(232, 106, 10, 255), width=int(9 * k), joint="curve")
    return sprite(size, size * 1.3, fn)


def pop_scale(lt, start, dur=0.35, s=1.9):
    p = prog(lt, start, dur)
    return (0.3 + 0.7 * ease_out_back(p, s)) if p > 0 else 0.0, clamp(p * 3)


# ================================================================ background / overlays
def make_background(top=(255, 248, 232), bottom=(255, 214, 168), dot=(255, 160, 60, 28)):
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    img = np.array(top, float) * (1 - y[..., None]) + np.array(bottom, float) * y[..., None]
    img = np.broadcast_to(img, (H, W, 3)).copy()
    d = np.sqrt((x - 0.5) ** 2 + ((y - 0.5) * 1.6) ** 2)
    glow = np.exp(-(d ** 2) / 0.12)[..., None]
    img = img * (1 - 0.35 * glow) + np.array([255, 255, 245]) * 0.35 * glow
    bg = Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA")
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for gy in range(0, H + 120, 120):
        for gx in range(0, W + 120, 120):
            ox = 60 if (gy // 120) % 2 else 0
            dd.ellipse((gx + ox - 9, gy - 9, gx + ox + 9, gy + 9), fill=dot)
    bg.alpha_composite(dots)
    return bg


def make_badge(number, color=(236, 110, 20)):
    t = text_img(f"{SERIES}  #{number}", 38)
    img = Image.new("RGBA", (t.width + 60, t.height + 30), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=img.height // 2,
                                          fill=color + (235,))
    img.alpha_composite(t, (30, 15))
    return img


TELOP_Y = 400


def draw_telop(frame, lt, dur, text, stroke_fill=(214, 84, 0)):
    if not text:
        return
    start = 0.2
    p = prog(lt, start, 0.35)
    if p <= 0:
        return
    s = 0.4 + 0.6 * ease_out_back(p)
    a = clamp(p * 3) * (1 - prog(lt, dur - 0.12, 0.12))
    img = text_img(text, 104, fill=(255, 255, 255), stroke=14, stroke_fill=stroke_fill)
    sh = text_img(text, 104, fill=(120, 50, 0), stroke=14, stroke_fill=(120, 50, 0))
    paste_center(frame, scaled(sh, s), W / 2 + 6, TELOP_Y + 8, alpha=0.35 * a)
    paste_center(frame, scaled(img, s), W / 2, TELOP_Y, alpha=a)


BUBBLE_LEFT, BUBBLE_Y = 285, 1500


def draw_bubble(frame, text, a, color=(236, 128, 30)):
    key = ("bubble", text, color)
    if key not in _text_cache:
        txt = text_img(text, 46, fill=(70, 36, 10))
        tail = 34
        box = Image.new("RGBA", (txt.width + 70 + tail, txt.height + 44), (0, 0, 0, 0))
        d = ImageDraw.Draw(box)
        d.rounded_rectangle((tail, 0, box.width - 1, box.height - 1), radius=30,
                            fill=(255, 255, 255, 245), outline=color + (255,), width=5)
        cy = box.height / 2
        d.polygon([(2, cy + 4), (tail + 6, cy - 18), (tail + 6, cy + 18)], fill=(255, 255, 255, 245))
        d.line([(tail + 3, cy - 18), (2, cy + 4), (tail + 3, cy + 18)], fill=color + (255,), width=5)
        box.alpha_composite(txt, (tail + 35, 22))
        _text_cache[key] = box
    box = _text_cache[key]
    frame.alpha_composite(with_alpha(box, a), (BUBBLE_LEFT, int(BUBBLE_Y - box.height / 2)))


# ================================================================ dog「コロ」
DOG_W, DOG_H = 320, 400
DOG_SCALE = 0.875
DOG_X, DOG_Y = 145, 1520
_dog_cache = {}


def dog_sprite(mouth, eyes):
    """柴犬「コロ」。mouth: 0(閉)〜5(大きく開く), eyes: open / blink / happy"""
    key = (mouth, eyes)
    if key in _dog_cache:
        return _dog_cache[key]
    ss = 3
    img = Image.new("RGBA", (DOG_W * ss, DOG_H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def E(cx, cy, w, h, **kw):
        d.ellipse(((cx - w / 2) * ss, (cy - h / 2) * ss, (cx + w / 2) * ss, (cy + h / 2) * ss), **kw)

    def P(pts, **kw):
        d.polygon([(x * ss, y * ss) for x, y in pts], **kw)

    fur, fur_dark, white = (236, 158, 72), (206, 122, 46), (255, 248, 238)
    ink = (52, 34, 24)
    E(160, 318, 230, 150, fill=fur_dark)
    E(160, 314, 220, 140, fill=fur)
    E(160, 318, 120, 112, fill=white)
    d.rounded_rectangle((92 * ss, 252 * ss, 228 * ss, 272 * ss), radius=10 * ss, fill=(214, 52, 52))
    E(160, 290, 38, 34, fill=(247, 140, 20), outline=(214, 100, 10), width=2 * ss)
    E(166, 274, 16, 8, fill=(74, 150, 52))
    for sgn in (-1, 1):
        P([(160 + sgn * 100, 100), (160 + sgn * 78, 12), (160 + sgn * 22, 62)], fill=fur_dark)
        P([(160 + sgn * 92, 88), (160 + sgn * 76, 30), (160 + sgn * 40, 64)], fill=(250, 206, 172))
    E(160, 162, 276, 236, fill=fur_dark)
    E(160, 158, 266, 226, fill=fur)
    E(108, 206, 118, 92, fill=white)
    E(212, 206, 118, 92, fill=white)
    E(160, 204, 116, 96, fill=white)
    E(118, 116, 30, 17, fill=white)
    E(202, 116, 30, 17, fill=white)
    E(84, 196, 34, 20, fill=(255, 160, 150))
    E(236, 196, 34, 20, fill=(255, 160, 150))
    for ex in (118, 202):
        if eyes == "open":
            E(ex, 150, 30, 38, fill=ink)
            E(ex - 5, 141, 11, 13, fill=(255, 255, 255))
            E(ex + 6, 158, 5, 5, fill=(255, 255, 255))
        elif eyes == "blink":
            d.arc(((ex - 15) * ss, 140 * ss, (ex + 15) * ss, 162 * ss), 20, 160, fill=ink, width=5 * ss)
        else:
            d.arc(((ex - 16) * ss, 140 * ss, (ex + 16) * ss, 166 * ss), 200, 340, fill=ink, width=6 * ss)
    if mouth > 0:
        h = 8 + mouth * 8
        E(160, 214 + h / 2, 40 + mouth * 3, h, fill=(130, 34, 34))
        E(160, 214 + h * 0.8, 26 + mouth * 2, h * 0.45, fill=(246, 120, 130))
    d.arc((136 * ss, 186 * ss, 162 * ss, 214 * ss), 20, 160, fill=ink, width=4 * ss)
    d.arc((158 * ss, 186 * ss, 184 * ss, 214 * ss), 20, 160, fill=ink, width=4 * ss)
    E(160, 184, 44, 30, fill=ink)
    E(153, 178, 13, 7, fill=(120, 110, 105))
    img = img.resize((int(DOG_W * DOG_SCALE), int(DOG_H * DOG_SCALE)), Image.LANCZOS)
    _dog_cache[key] = img
    return img


def draw_dog(frame, tr, mouth_level, jump, happy):
    blink = (tr % 3.1) < 0.13
    eyes = "happy" if (happy or jump > 0) else ("blink" if blink else "open")
    img = dog_sprite(mouth_level, eyes)
    tilt = math.sin(tr * 1.7) * 3 + (2.5 * math.sin(tr * 9) if mouth_level else 0)
    img = rotated(img, tilt)
    bob = math.sin(tr * 3.2) * 5
    sh_w = 200 * (1 - 0.3 * jump)
    shadow = Image.new("RGBA", (int(sh_w) + 40, 70), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((20, 20, 20 + sh_w, 50), fill=(150, 80, 20, 70))
    paste_center(frame, shadow.filter(ImageFilter.GaussianBlur(8)), DOG_X, DOG_Y + 150)
    paste_center(frame, img, DOG_X, DOG_Y + bob - 70 * jump)


# ================================================================ audio
def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def add(buf, sig, at):
    i = int(at * SR)
    if i < 0:
        sig, i = sig[-i:], 0
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i]


def pluck(freq, dur, amp=0.3):
    tt = np.arange(int(dur * SR)) / SR
    out = np.zeros(len(tt))
    for k in range(1, 8):
        out += (1 / k ** 1.4) * np.sin(2 * np.pi * freq * k * tt) * np.exp(-tt * (3.5 + 1.8 * k))
    return out * np.minimum(1, tt / 0.003) * amp


class SFX:
    """効果音。時刻は実時間（秒）。"""

    def __init__(self, total):
        self.buf = np.zeros(total)

    def pop(self, at, f0=500, f1=1100, amp=0.35):
        tt = np.arange(int(0.09 * SR)) / SR
        f = f0 + (f1 - f0) * (tt / tt[-1])
        add(self.buf, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 40) * amp, at)

    def whoosh(self, at, dur=0.45, amp=0.25):
        n = int(dur * SR)
        sm = np.convolve(np.random.randn(n), np.ones(40) / 40, mode="same")
        add(self.buf, sm * np.sin(np.linspace(0, np.pi, n)) ** 2 * amp * 3, at)

    def ding(self, at, amp=0.3):
        for m, d0 in ((84, 0), (88, 0.08), (91, 0.16)):
            tt = np.arange(int(1.0 * SR)) / SR
            f = midi_hz(m)
            s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt * 3.5)
            add(self.buf, s * amp * 0.5, at + d0)

    def thud(self, at, amp=0.45):
        tt = np.arange(int(0.25 * SR)) / SR
        f = 140 * np.exp(-tt * 12) + 50
        add(self.buf, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 14) * amp, at)

    def splash(self, at, amp=0.35):
        n = int(0.6 * SR)
        tt = np.arange(n) / SR
        noise = np.diff(np.random.randn(n + 1))
        sm = np.convolve(noise, np.ones(6) / 6, mode="same")
        add(self.buf, sm * np.exp(-tt * 7) * amp, at)
        for i in range(5):
            self.pop(at + 0.08 + i * 0.07, 900 + 200 * i, 1600 + 150 * i, 0.08)

    def chop(self, at, amp=0.4):
        n = int(0.12 * SR)
        tt = np.arange(n) / SR
        noise = np.diff(np.random.randn(n + 1))
        add(self.buf, noise * np.exp(-tt * 45) * amp * 0.6, at)
        self.thud(at, amp * 0.6)

    def shake(self, at, dur=0.8, amp=0.12):
        for i in range(int(dur / 0.09)):
            n = int(0.04 * SR)
            noise = np.diff(np.random.randn(n + 1)) * np.exp(-np.arange(n) / SR * 120)
            add(self.buf, noise * amp, at + i * 0.09)

    def boing(self, at, amp=0.3):
        tt = np.arange(int(0.4 * SR)) / SR
        f = 220 + 160 * np.sin(tt * 40) * np.exp(-tt * 6) + 200 * tt
        add(self.buf, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 6) * amp, at)


CHORDS = {
    "uke": [([60, 64, 67, 72], 48), ([59, 62, 67, 71], 43), ([60, 64, 69, 72], 45), ([60, 65, 69, 72], 41)],
    "fresh": [([62, 65, 69, 74], 50), ([60, 64, 67, 72], 48), ([59, 62, 67, 71], 43), ([60, 64, 67, 72], 48)],
    "sweet": [([65, 69, 72, 77], 41), ([64, 67, 72, 76], 48), ([62, 65, 69, 74], 50), ([60, 64, 67, 72], 48)],
}
MELODY = {
    "uke": [[72, 74, 76, 79], [79, 77, 74, 71], [72, 76, 81, 79], [77, 76, 74, 72]],
    "fresh": [[74, 77, 81, 79], [76, 79, 84, 79], [74, 71, 74, 79], [76, 74, 72, 72]],
    "sweet": [[81, 79, 77, 76], [79, 76, 72, 76], [77, 74, 77, 81], [79, 76, 72, 72]],
}


def make_bgm(total_sec, style="uke", bpm=118):
    total = int(total_sec * SR)
    bgm = np.zeros(total)
    beat = 60 / bpm
    chords, melody = CHORDS[style], MELODY[style]
    pattern = [(0, 1.0), (1, 0.6), (1.5, 0.45), (2, 0.85), (2.5, 0.45), (3, 0.6), (3.5, 0.45)]
    bar, t0 = 0, 0.0
    while t0 < total_sec:
        notes, root = chords[bar % 4]
        for pos, vel in pattern:
            order = notes if int(pos * 2) % 2 == 0 else notes[::-1]
            for idx, m in enumerate(order):
                add(bgm, pluck(midi_hz(m), 1.2, 0.11 * vel), t0 + pos * beat + idx * 0.012)
        for pos in (0, 2):
            tt = np.arange(int(beat * 1.6 * SR)) / SR
            f = midi_hz(root)
            b = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 3)
            add(bgm, b * 0.22 * np.minimum(1, tt / 0.01), t0 + pos * beat)
        for pos in (0.5, 1.5, 2.5, 3.5):
            n = int(0.05 * SR)
            add(bgm, np.diff(np.random.randn(n + 1)) * np.exp(-np.arange(n) / SR * 90) * 0.035, t0 + pos * beat)
        for i, m in enumerate(melody[bar % 4]):
            tt = np.arange(int(0.8 * SR)) / SR
            f = midi_hz(m)
            bell = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * f * 3.01 * tt)) * np.exp(-tt * 4)
            add(bgm, bell * 0.05 * np.minimum(1, tt / 0.005), t0 + i * beat)
        t0 += 4 * beat
        bar += 1
    return bgm


_voice_cache = {}


def synth_voice(text, tmpdir):
    """Open JTalkで読み上げ、前後の無音を削った配列（SR）を返す。使えなければ None。"""
    if text in _voice_cache:
        return _voice_cache[text]
    if not shutil.which("open_jtalk") or not os.path.exists(JTALK_VOICE):
        return None
    wav_path = os.path.join(tmpdir, "jtalk.wav")
    subprocess.run(["open_jtalk", "-x", JTALK_DIC, "-m", JTALK_VOICE, "-fm", str(VOICE_PITCH),
                    "-r", str(VOICE_SPEED), "-jf", str(VOICE_INTONATION), "-ow", wav_path],
                   input=text.encode("utf-8"), check=True)
    with wave.open(wav_path) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
        if w.getnchannels() == 2:
            x = x.reshape(-1, 2).mean(axis=1)
    if sr != SR:
        x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
    idx = np.where(np.abs(x) > 0.02 * np.abs(x).max())[0]
    if len(idx):
        x = x[max(0, idx[0] - int(0.02 * SR)): idx[-1] + int(0.05 * SR)]
    x = x / (np.abs(x).max() + 1e-9) * 0.8
    _voice_cache[text] = x
    return x


def mouth_levels(voice, frames):
    hop = SR // FPS
    env = np.array([np.sqrt(np.mean(voice[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(frames)])
    ref = np.percentile(env[env > 0.01], 90) if np.any(env > 0.01) else 1
    lv = np.clip(env / ref * 5, 0, 5)
    lv[env < 0.015] = 0
    return np.round(lv).astype(int)


# ================================================================ timeline
class Scene:
    """1シーン。

    draw(frame, lt, scene) : lt はシーン内の経過秒。scene.dur でシーンの長さがわかる。
    line                   : コロのセリフ（読み上げる文）。sub は吹き出しの文（改行入り）。
    say                    : [(シーン内秒, 文)] 追加の読み上げ（数え上げなど。吹き出しは出さない）
    sfx                    : [(シーン内秒, "pop", {kw})] 効果音
    jumps                  : コロが跳ねるシーン内秒
    """

    def __init__(self, draw, min_dur, telop=None, line=None, sub=None, line_at=0.3, say=(), sfx=(),
                 jumps=(), happy=False, tail=0.45, whoosh=True):
        self.draw, self.min_dur, self.telop = draw, min_dur, telop
        self.line, self.sub, self.line_at = line, sub, line_at
        self.say, self.sfx, self.jumps, self.happy = list(say), list(sfx), list(jumps), happy
        self.tail, self.whoosh = tail, whoosh
        self.dur = min_dur
        self.start = 0.0
        self.line_len = 0.0


class Video:
    def __init__(self, number, scenes, out_name, bg=None, badge_color=(236, 110, 20),
                 telop_stroke=(214, 84, 0), bubble_color=(236, 128, 30), bgm="uke", bpm=118):
        self.number, self.scenes, self.out_name = number, scenes, out_name
        self.bg = make_background(**(bg or {}))
        self.badge = make_badge(number, badge_color)
        self.telop_stroke, self.bubble_color = telop_stroke, bubble_color
        self.bgm_style, self.bpm = bgm, bpm
        self.bookmark = make_bookmark(110)

    # ---- timing
    def layout(self, tmp):
        t = 0.0
        has_voice = True
        for sc in self.scenes:
            need = sc.min_dur
            if sc.line:
                v = synth_voice(sc.line, tmp)
                if v is None:
                    has_voice = False
                else:
                    sc.line_len = len(v) / SR
                    need = max(need, sc.line_at + sc.line_len + sc.tail)
            for at, text in sc.say:
                v = synth_voice(text, tmp)
                if v is not None:
                    need = max(need, at + len(v) / SR + sc.tail)
            sc.dur = need
            sc.start = t
            t += need
        self.total = t
        if not has_voice:
            print("open_jtalk か声のモデルが見つからないため、音声なしで書き出します", file=sys.stderr)
        return has_voice

    def scene_at(self, tr):
        for sc in self.scenes:
            if tr < sc.start + sc.dur:
                return sc
        return self.scenes[-1]

    # ---- audio
    def build_audio(self, tmp, path):
        total = int(self.total * SR)
        voice = np.zeros(total)
        sfx = SFX(total)
        for i, sc in enumerate(self.scenes):
            if sc.line:
                v = synth_voice(sc.line, tmp)
                if v is not None:
                    add(voice, v, sc.start + sc.line_at)
            for at, text in sc.say:
                v = synth_voice(text, tmp)
                if v is not None:
                    add(voice, v, sc.start + at)
            if i > 0 and sc.whoosh:
                sfx.whoosh(sc.start - 0.05)
            if sc.telop:
                sfx.pop(sc.start + 0.2, 400, 900)
            for at, kind, kw in sc.sfx:
                getattr(sfx, kind)(sc.start + at, **kw)
            for at in sc.jumps:
                sfx.boing(sc.start + at, 0.12)
        bgm = make_bgm(self.total, self.bgm_style, self.bpm)
        k = int(0.15 * SR)
        env = np.convolve(np.abs(voice), np.ones(k) / k, mode="same")
        duck = 1 - 0.55 * np.clip(env / 0.05, 0, 1)
        mix = bgm * 0.8 * duck + sfx.buf * 0.8 + voice * 0.95
        fade = int(1.2 * SR)
        mix[-fade:] *= np.linspace(1, 0, fade)
        mix[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))
        mix = np.tanh(mix * 1.1) * 0.9
        pcm = (np.stack([mix, mix], axis=1) * 32767).astype(np.int16)
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        return voice

    # ---- frames
    def render_frame(self, tr, mouth=0):
        sc = self.scene_at(tr)
        lt = tr - sc.start
        frame = self.bg.copy()
        sc.draw(frame, lt, sc)
        if sc is not self.scenes[0] and lt < 0.25:
            frame.alpha_composite(Image.new("RGBA", frame.size, (255, 255, 255, int(200 * (1 - lt / 0.25)))))
        paste_center(frame, self.badge, W / 2, 190)
        draw_telop(frame, lt, sc.dur, sc.telop, self.telop_stroke)
        jump = 0.0
        for j in sc.jumps:
            p = prog(lt, j, 0.45)
            if 0 < p < 1:
                jump = max(jump, math.sin(p * math.pi))
        draw_dog(frame, tr, mouth, jump, sc.happy)
        if sc.sub:
            a = clamp((lt - (sc.line_at - 0.15)) / 0.12) * (1 - prog(lt, sc.dur - 0.12, 0.12))
            if a > 0:
                draw_bubble(frame, sc.sub, a, self.bubble_color)
        return frame.convert("RGB")

    def preview(self, times, path, cols=3, scale=1 / 3):
        with tempfile.TemporaryDirectory() as tmp:
            self.layout(tmp)
        ims = [self.render_frame(t, 3).resize((int(W * scale), int(H * scale))) for t in times]
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (int(W * scale) * cols, int(H * scale) * rows), "white")
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % cols) * im.width, (i // cols) * im.height))
        sheet.save(path)
        return [(round(sc.start, 2), round(sc.dur, 2)) for sc in self.scenes]

    def render(self, out=None):
        out = out or os.path.join(HERE, "out", self.out_name)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            self.layout(tmp)
            wav = os.path.join(tmp, "audio.wav")
            voice = self.build_audio(tmp, wav)
            frames = int(self.total * FPS)
            mouths = mouth_levels(voice, frames)
            cmd = ["ffmpeg", "-y", "-loglevel", "error",
                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                   "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            for f in range(frames):
                proc.stdin.write(self.render_frame(f / FPS, int(mouths[f])).tobytes())
                if f % 150 == 0:
                    print(f"{self.out_name}: frame {f}/{frames}", flush=True)
            proc.stdin.close()
            proc.wait()
        print("wrote", out, f"({self.total:.1f}s)")


def outro_draw(subject_fn, cx=W / 2, cy=990, bookmark=None):
    """締めシーン：主役がぴょこっと出て、キラキラと保存マーク。"""
    bm = bookmark or make_bookmark(110)

    def draw(frame, lt, sc):
        p = ease_out_back(prog(lt, 0.0, 0.5), 1.5)
        bob = math.sin(lt * 4) * 14
        subject_fn(frame, cx, cy + bob, 0.5 + 0.5 * p, lt)
        draw_sparkles(frame, lt, cx, cy, 360, 9, n=8)
        k = ease_out_back(prog(lt, 1.0, 0.4))
        if k > 0:
            paste_center(frame, scaled(bm, 0.3 + 0.7 * k), cx + 330, cy - 280, alpha=clamp(k * 2))
    return draw


OUTRO_LINE = "保存して、誰かに教えてあげてね！"
OUTRO_SUB = "保存して、誰かに\n教えてあげてね！"
OUTRO_TELOP = "保存して\n試してみて！"
