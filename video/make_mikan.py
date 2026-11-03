#!/usr/bin/env python3
"""台本 #1「みかんの房の数、むく前にわかる？」を縦型動画（1080x1920, 30fps）にする。

イラスト・テロップ・字幕はPillowで描画し、BGMと効果音はnumpyで合成、ffmpegでMP4にまとめる。
使い方: python3 video/make_mikan.py [出力パス]
"""
import math
import os
import random
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
DURATION = 25.5
SR = 44100
FONT_PATH = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"

random.seed(7)
np.random.seed(7)


# ---------------------------------------------------------------- utilities
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, start, dur):
    return clamp((t - start) / dur)


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 3 * x * x - 2 * x * x * x


def ease_out_back(x, s=1.9):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def paste_center(frame, img, cx, cy, alpha=1.0):
    if alpha <= 0 or img.width == 0 or img.height == 0:
        return
    if alpha < 1.0:
        img = img.copy()
        a = img.getchannel("A").point(lambda v: int(v * alpha))
        img.putalpha(a)
    frame.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def scaled(img, s):
    if abs(s - 1.0) < 1e-3:
        return img
    w, h = max(1, int(img.width * s)), max(1, int(img.height * s))
    return img.resize((w, h), Image.BILINEAR)


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
    d = ImageDraw.Draw(img)
    d.multiline_text((4 - box[0], 4 - box[1]), text, font=f, fill=fill, stroke_width=stroke,
                     stroke_fill=stroke_fill, spacing=spacing, align="center")
    _text_cache[key] = img
    return img


# ---------------------------------------------------------------- assets
def make_background():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    top = np.array([255, 248, 232], float)
    bot = np.array([255, 214, 168], float)
    img = top * (1 - y[..., None]) + bot * y[..., None]
    img = np.broadcast_to(img, (H, W, 3)).copy()
    # 中央のやわらかいスポットライト
    d = np.sqrt((x - 0.5) ** 2 + ((y - 0.5) * 1.6) ** 2)
    glow = np.exp(-(d ** 2) / 0.12)[..., None]
    img = img * (1 - 0.35 * glow) + np.array([255, 255, 245]) * 0.35 * glow
    # うっすら水玉
    bg = Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA")
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for gy in range(0, H + 120, 120):
        for gx in range(0, W + 120, 120):
            ox = 60 if (gy // 120) % 2 else 0
            dd.ellipse((gx + ox - 9, gy - 9, gx + ox + 9, gy + 9), fill=(255, 160, 60, 28))
    bg.alpha_composite(dots)
    return bg


def sphere_shading(size, squash=1.0, light=(-0.35, -0.42)):
    """オレンジ色の球のシェーディング（RGBA numpy配列）。"""
    n = size
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    nx = (xx - n / 2) / (n / 2)
    ny = (yy - n / 2) / (n / 2 * squash)
    r = np.sqrt(nx ** 2 + ny ** 2)
    inside = r <= 1.0
    lx, ly = light
    dl = np.sqrt((nx - lx) ** 2 + (ny - ly) ** 2)
    light_c = np.array([255, 196, 84], float)
    base_c = np.array([240, 120, 14], float)
    dark_c = np.array([190, 72, 6], float)
    t = np.clip(dl / 1.25, 0, 1)[..., None]
    col = light_c * (1 - t) + base_c * t
    edge = np.clip((r - 0.75) / 0.25, 0, 1)[..., None] ** 1.5
    col = col * (1 - 0.55 * edge) + dark_c * 0.55 * edge
    spec = np.exp(-(dl ** 2) / 0.018)[..., None]
    col = col * (1 - 0.55 * spec) + 255 * 0.55 * spec
    alpha = np.clip((1.0 - r) * n / 3, 0, 1) * 255
    out = np.zeros((n, n, 4), np.uint8)
    out[..., :3] = col.clip(0, 255)
    out[..., 3] = (alpha * inside).astype(np.uint8)
    return out, nx, ny, r


def add_peel_texture(img, count, rad_px, mask_fn):
    """皮のつぶつぶ（油胞）を描く。"""
    tex = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(tex)
    n = img.width
    for _ in range(count):
        px, py = random.uniform(0, n), random.uniform(0, n)
        if not mask_fn(px, py):
            continue
        rr = random.uniform(rad_px * 0.6, rad_px * 1.3)
        if random.random() < 0.55:
            d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=(170, 70, 0, 38))
        else:
            d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=(255, 230, 160, 40))
    img.alpha_composite(tex)


def make_side_mandarin(diam):
    """横から見たみかん（ヘタと葉つき）。"""
    ss = 2
    n = int(diam * 1.4) * ss
    body_n = diam * ss
    arr, nx, ny, r = sphere_shading(body_n, squash=0.86)
    body = Image.fromarray(arr, "RGBA")
    add_peel_texture(body, 2600, 4.0 * ss,
                     lambda px, py: ((px - body_n / 2) / (body_n / 2)) ** 2
                     + ((py - body_n / 2) / (body_n / 2 * 0.86)) ** 2 < 0.93)
    # テクスチャを本体の形に切り抜く
    body.putalpha(Image.fromarray(arr[..., 3]))
    canvas = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    canvas.alpha_composite(body, ((n - body_n) // 2, (n - body_n) // 2))
    d = ImageDraw.Draw(canvas)
    cx, top = n / 2, (n - body_n) / 2 + body_n / 2 * (1 - 0.86)
    # 葉
    leaf = Image.new("RGBA", (int(body_n * 0.42), int(body_n * 0.2)), (0, 0, 0, 0))
    ld = ImageDraw.Draw(leaf)
    ld.ellipse((0, 0, leaf.width - 1, leaf.height - 1), fill=(74, 150, 52, 255))
    ld.line((leaf.width * 0.05, leaf.height / 2, leaf.width * 0.95, leaf.height / 2),
            fill=(120, 190, 90, 255), width=3 * ss)
    leaf = leaf.rotate(28, expand=True, resample=Image.BICUBIC)
    canvas.alpha_composite(leaf, (int(cx - 6 * ss), int(top - leaf.height * 0.78)))
    # ヘタ
    sr = body_n * 0.055
    d.ellipse((cx - sr, top - sr * 0.9, cx + sr, top + sr * 0.6), fill=(96, 120, 40, 255))
    d.ellipse((cx - sr * 0.5, top - sr * 0.6, cx + sr * 0.5, top + sr * 0.1), fill=(140, 160, 70, 255))
    return canvas.resize((n // ss, n // ss), Image.LANCZOS)


TOP_D = 860          # 真上から見たみかんの直径
DOT_RING_R = 118     # 点が並ぶ輪の半径
N_DOTS = 10


def make_top_mandarin(diam):
    """真上から見たみかん（ヘタなし、中央に点の輪）。"""
    ss = 2
    n = diam * ss
    arr, nx, ny, r = sphere_shading(n, squash=1.0, light=(-0.3, -0.35))
    img = Image.fromarray(arr, "RGBA")
    add_peel_texture(img, 5200, 4.5 * ss,
                     lambda px, py: ((px - n / 2) ** 2 + (py - n / 2) ** 2) < (n / 2 * 0.95) ** 2)
    img.putalpha(Image.fromarray(arr[..., 3]))
    d = ImageDraw.Draw(img)
    c = n / 2
    # ヘタがついていた部分（少し黄緑がかった淡い円）
    cr = 175 * ss
    pale = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pale)
    pd.ellipse((c - cr, c - cr, c + cr, c + cr), fill=(250, 214, 120, 255))
    pale = pale.filter(ImageFilter.GaussianBlur(14 * ss))
    img.alpha_composite(pale)
    d.ellipse((c - 34 * ss, c - 34 * ss, c + 34 * ss, c + 34 * ss), fill=(214, 170, 80, 255))
    return img.resize((diam, diam), Image.LANCZOS)


def dot_positions(cx, cy, scale=1.0):
    pts = []
    for i in range(N_DOTS):
        a = -math.pi / 2 + i * 2 * math.pi / N_DOTS
        pts.append((cx + math.cos(a) * DOT_RING_R * scale, cy + math.sin(a) * DOT_RING_R * scale))
    return pts


def make_stem_cap(size):
    ss = 2
    n = size * ss
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = n / 2
    pts = []
    for i in range(10):
        a = i * math.pi / 5
        rr = n * 0.48 if i % 2 == 0 else n * 0.36
        pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
    d.polygon(pts, fill=(88, 128, 44, 255))
    d.ellipse((c - n * 0.2, c - n * 0.2, c + n * 0.2, c + n * 0.2), fill=(130, 150, 60, 255))
    d.ellipse((c - n * 0.08, c - n * 0.08, c + n * 0.08, c + n * 0.08), fill=(90, 80, 40, 255))
    return img.resize((size, size), Image.LANCZOS)


def make_segment(length, width, strands=False, strand_progress=1.0):
    """房（じょうのう）1つ。縦長のレンズ形。"""
    ss = 2
    L, Wd = length * ss, width * ss
    pad = 8 * ss
    img = Image.new("RGBA", (Wd + pad * 2, L + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 外形（三日月っぽく片側を膨らませる）
    pts_out, pts_in = [], []
    steps = 60
    for i in range(steps + 1):
        t = i / steps
        y = pad + t * L
        bulge = math.sin(math.pi * t)
        pts_out.append((pad + Wd * 0.5 + Wd * 0.5 * bulge, y))
        pts_in.append((pad + Wd * 0.5 - Wd * 0.32 * bulge, y))
    poly = pts_out + pts_in[::-1]
    d.polygon(poly, fill=(255, 166, 40, 255), outline=(236, 128, 20, 255))
    # 内側のつやと果肉の粒
    hl = []
    for i in range(steps + 1):
        t = i / steps
        y = pad + L * (0.12 + 0.76 * t)
        b = math.sin(math.pi * t)
        hl.append((pad + Wd * 0.55 + Wd * 0.3 * b, y))
    d.line(hl, fill=(255, 214, 120, 255), width=int(7 * ss))
    for _ in range(int(L * Wd / 900)):
        t = random.uniform(0.1, 0.9)
        b = math.sin(math.pi * t)
        x = random.uniform(pad + Wd * 0.5 - Wd * 0.25 * b, pad + Wd * 0.5 + Wd * 0.42 * b)
        y = pad + t * L
        rr = random.uniform(3, 7) * ss
        d.ellipse((x - rr, y - rr * 2, x + rr, y + rr * 2), fill=(255, 190, 70, 160))
    if strands:
        rng = random.Random(3)
        for k in range(7):
            p = clamp(strand_progress * 7 - k)
            if p <= 0:
                continue
            x0 = pad + Wd * (0.35 + 0.06 * k)
            pts = []
            for i in range(int(40 * p) + 1):
                t = i / 40
                y = pad + L * (0.08 + 0.84 * t)
                b = math.sin(math.pi * (0.08 + 0.84 * t))
                x = x0 + Wd * 0.15 * b * (k - 2) / 4 + math.sin(t * 9 + k) * 6 * ss
                pts.append((x, y))
            if len(pts) > 1:
                d.line(pts, fill=(255, 252, 240, 235), width=int(rng.uniform(4, 7) * ss))
    return img.resize((img.width // ss, img.height // ss), Image.LANCZOS)


def make_sparkle(size, color=(255, 255, 255)):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size / 2
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        rr = size * 0.5 if i % 2 == 0 else size * 0.12
        pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
    d.polygon(pts, fill=color + (255,))
    return img


def make_bookmark(size):
    img = Image.new("RGBA", (size, int(size * 1.3)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w, h = img.size
    d.polygon([(4, 4), (w - 4, 4), (w - 4, h - 4), (w / 2, h * 0.7), (4, h - 4)],
              fill=(255, 255, 255, 255), outline=(232, 106, 10, 255))
    d.line([(4, 4), (w - 4, 4), (w - 4, h - 4), (w / 2, h * 0.7), (4, h - 4), (4, 4)],
           fill=(232, 106, 10, 255), width=10)
    return img


# ---------------------------------------------------------------- script
TELOPS = [  # (開始, 終了, テキスト)
    (0.3, 3.0, "むく前に\n房の数わかる？"),
    (3.4, 8.0, "ヘタの裏の\n点の数を数える"),
    (8.0, 14.0, "点が10個なら…"),
    (16.0, 19.0, "ほぼ同じ数！"),
    (19.4, 23.0, "白い筋も\n栄養あり"),
    (23.3, DURATION, "保存して\n試してみて！"),
]

SUBTITLES = [  # ナレーション（音声なしの代わりに字幕で表示）
    (0.2, 3.0, "みかんの房の数、むく前に\nわかるって知ってた？"),
    (3.2, 8.0, "ヘタを取って、\n裏の点を数えてみて"),
    (8.2, 14.0, "この点の数が…"),
    (14.2, 19.0, "房の数とほぼ同じなんです！"),
    (19.2, 23.0, "白い筋にも栄養があるから、\n取らずに食べてOK"),
    (23.2, DURATION, "保存して誰かに\n教えてあげてね！"),
]

COUNT_START, COUNT_STEP = 8.6, 0.45
SEG_START, SEG_STEP = 14.25, 0.13
STEM_POP = 4.6


# ---------------------------------------------------------------- render
class Assets:
    def __init__(self):
        self.bg = make_background()
        self.side = make_side_mandarin(600)
        self.top = make_top_mandarin(TOP_D)
        self.stem = make_stem_cap(230)
        self.seg = make_segment(330, 130)
        self.seg_rot = [self.seg.rotate(-i * 36, expand=True, resample=Image.BICUBIC) for i in range(N_DOTS)]
        self.big_segs = [make_segment(900, 360, strands=True, strand_progress=p / 20) for p in range(21)]
        self.sparkle = make_sparkle(90)
        self.sparkle_y = make_sparkle(70, (255, 236, 150))
        self.bookmark = make_bookmark(110)
        self.badge = self._badge()
        self.shadow = self._shadow(560, 90)

    def _badge(self):
        t = text_img("知らなかった！野菜と果物のヒミツ  #1", 38, fill=(255, 255, 255))
        img = Image.new("RGBA", (t.width + 60, t.height + 30), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=img.height // 2, fill=(236, 110, 20, 235))
        img.alpha_composite(t, (30, 15))
        return img

    def _shadow(self, w, h):
        img = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((40, 40, 40 + w, 40 + h), fill=(150, 80, 20, 90))
        return img.filter(ImageFilter.GaussianBlur(18))


def draw_telop(frame, t):
    for start, end, text in TELOPS:
        if start <= t < end:
            p = prog(t, start, 0.35)
            s = 0.4 + 0.6 * ease_out_back(p)
            img = text_img(text, 104, fill=(255, 255, 255), stroke=14, stroke_fill=(214, 84, 0))
            # ドロップシャドウ
            sh = text_img(text, 104, fill=(120, 50, 0), stroke=14, stroke_fill=(120, 50, 0))
            a = clamp(p * 3) * (1 - prog(t, end - 0.15, 0.15))
            paste_center(frame, scaled(sh, s), W / 2 + 6, 400 + 8, alpha=0.35 * a)
            paste_center(frame, scaled(img, s), W / 2, 400, alpha=a)


def draw_subtitle(frame, t):
    for start, end, text in SUBTITLES:
        if start <= t < end:
            a = clamp((t - start) / 0.2) * (1 - prog(t, end - 0.15, 0.15))
            txt = text_img(text, 50, fill=(255, 255, 255))
            box = Image.new("RGBA", (txt.width + 70, txt.height + 44), (0, 0, 0, 0))
            d = ImageDraw.Draw(box)
            d.rounded_rectangle((0, 0, box.width - 1, box.height - 1), radius=28, fill=(40, 24, 10, 170))
            box.alpha_composite(txt, (35, 22))
            paste_center(frame, box, W / 2, 1585, alpha=a)


def draw_sparkles(frame, A, t, cx, cy, radius, seed, n=6, start=0.0):
    rng = random.Random(seed)
    for i in range(n):
        ph = rng.uniform(0, 1)
        per = rng.uniform(0.9, 1.4)
        lt = ((t - start) / per + ph) % 1.0
        s = math.sin(lt * math.pi)
        ang = rng.uniform(0, 2 * math.pi)
        rr = radius * rng.uniform(0.9, 1.25)
        spr = A.sparkle if i % 2 else A.sparkle_y
        paste_center(frame, scaled(spr, 0.3 + 0.7 * s), cx + math.cos(ang) * rr, cy + math.sin(ang) * rr, alpha=s)


def scene_roll(frame, A, t):
    cx_end, cy = W / 2, 980
    D = 600
    p = ease_out_cubic(prog(t, 0.0, 2.2))
    dist = math.pi * D * 1.0
    x = cx_end - dist * (1 - p)
    ang = -math.degrees((x - cx_end) / (D / 2))   # 1回転ぴったりで止まる
    # 着地のぽよん
    q = prog(t, 2.15, 0.5)
    squash = 1 + 0.08 * math.sin(q * math.pi * 3) * (1 - q) if q > 0 else 1
    img = A.side.rotate(ang, resample=Image.BICUBIC)
    img = img.resize((int(img.width * (2 - squash)), int(img.height * squash)), Image.BILINEAR)
    paste_center(frame, A.shadow, x, cy + D * 0.4 + 20, alpha=0.9)
    paste_center(frame, img, x, cy + (1 - squash) * D * 0.4)
    if t > 2.3:
        draw_sparkles(frame, A, t, cx_end, cy, 380, 1, n=5, start=2.3)


def draw_top_view(frame, A, t, scale, alpha, show_stem, stem_t, count_upto, glow):
    cx, cy = W / 2, 990
    paste_center(frame, scaled(A.top, scale), cx, cy, alpha=alpha)
    d = ImageDraw.Draw(frame)
    pts = dot_positions(cx, cy, scale)
    # 点の輪
    for i, (px, py) in enumerate(pts):
        r = 15 * scale
        if count_upto is not None and i < count_upto:
            k = prog(t, COUNT_START + i * COUNT_STEP, 0.25)
            r *= 1 + 0.5 * math.sin(k * math.pi) + 0.15
        g = 0.5 + 0.5 * math.sin(t * 6) if glow else 0
        if glow:
            d.ellipse((px - r * 1.9, py - r * 1.9, px + r * 1.9, py + r * 1.9),
                      fill=(255, 255, 220, int(60 + 50 * g)))
        d.ellipse((px - r, py - r, px + r, py + r), fill=(255, 253, 240, int(255 * alpha)),
                  outline=(230, 190, 120, int(255 * alpha)), width=3)
    if show_stem:
        p = prog(t, STEM_POP, 0.7)
        wiggle = math.sin(t * 22) * 8 * (1 - p) if t < STEM_POP else 0
        sx = cx + 260 * ease_out_cubic(p)
        sy = cy - 520 * ease_out_cubic(p) + 300 * p * p
        st = A.stem.rotate(wiggle + 220 * p, resample=Image.BICUBIC, expand=True)
        paste_center(frame, scaled(st, scale), sx, sy, alpha=alpha * (1 - prog(t, STEM_POP + 0.4, 0.3)))
    # 番号
    if count_upto is not None:
        for i, (px, py) in enumerate(pts[:count_upto]):
            k = prog(t, COUNT_START + i * COUNT_STEP, 0.3)
            a = -math.pi / 2 + i * 2 * math.pi / N_DOTS
            nx, ny = cx + math.cos(a) * 250, cy + math.sin(a) * 250
            num = text_img(str(i + 1), 76, fill=(255, 255, 255), stroke=10, stroke_fill=(200, 70, 0))
            paste_center(frame, scaled(num, 0.3 + 0.7 * ease_out_back(k)), nx, ny, alpha=clamp(k * 3))
            d.line((px + (nx - px) * 0.28, py + (ny - py) * 0.28, px + (nx - px) * 0.62, py + (ny - py) * 0.62),
                   fill=(255, 255, 255, int(200 * k)), width=5)


def scene_top(frame, A, t):
    p = ease_out_cubic(prog(t, 3.0, 0.5))
    scale = 0.55 + 0.45 * p
    show_stem = t < STEM_POP + 0.8
    counting = t >= 8.0
    count_upto = None
    if counting:
        count_upto = sum(1 for i in range(N_DOTS) if t >= COUNT_START + i * COUNT_STEP)
    glow = STEM_POP + 0.5 < t < 8.0
    draw_top_view(frame, A, t, scale, clamp(p * 1.5), show_stem, t, count_upto, glow)
    if t > 13.3:
        # 「10個」の強調
        k = prog(t, 13.3, 0.3)
        lbl = text_img("10個", 120, fill=(255, 240, 90), stroke=14, stroke_fill=(190, 60, 0))
        paste_center(frame, scaled(lbl, 0.4 + 0.6 * ease_out_back(k)), W / 2, 990, alpha=clamp(k * 3))


def scene_flower(frame, A, t):
    cx, cy = W / 2, 950
    d = ImageDraw.Draw(frame)
    # 皮（下に敷く）
    peel_a = clamp((t - 14.0) / 0.3)
    paste_center(frame, A.shadow, cx, cy + 330, alpha=0.6 * peel_a)
    for i in range(N_DOTS):
        k = ease_out_back(prog(t, SEG_START + i * SEG_STEP, 0.45), 1.4)
        if k <= 0:
            continue
        a = -math.pi / 2 + i * 2 * math.pi / N_DOTS
        rr = 40 + 205 * k
        paste_center(frame, A.seg_rot[i], cx + math.cos(a) * rr, cy + math.sin(a) * rr, alpha=clamp(k * 2))
    # 中心の芯
    d.ellipse((cx - 38, cy - 38, cx + 38, cy + 38), fill=(255, 236, 190, int(255 * peel_a)))
    if t >= 15.9:
        k = prog(t, 15.9, 0.35)
        lbl = text_img("10房", 150, fill=(255, 240, 90), stroke=16, stroke_fill=(190, 60, 0))
        paste_center(frame, scaled(lbl, 0.4 + 0.6 * ease_out_back(k)), cx, cy, alpha=clamp(k * 3))
    if t >= 16.6:
        k = prog(t, 16.6, 0.3)
        eq = text_img("点 10個 ＝ 10房", 64, fill=(120, 50, 0))
        paste_center(frame, scaled(eq, 0.6 + 0.4 * ease_out_back(k)), cx, cy + 430, alpha=clamp(k * 3))
        draw_sparkles(frame, A, t, cx, cy, 300, 4, n=7, start=16.6)


def scene_strand(frame, A, t):
    cx, cy = W / 2, 1000
    p = ease_out_cubic(prog(t, 19.0, 0.4))
    sp = prog(t, 19.6, 1.6)
    seg = A.big_segs[int(round(sp * 20))]
    seg = seg.rotate(90, expand=True, resample=Image.BICUBIC)
    paste_center(frame, scaled(seg, 0.6 + 0.4 * p), cx, cy, alpha=clamp(p * 2))
    if t >= 21.0:
        k = prog(t, 21.0, 0.35)
        d = ImageDraw.Draw(frame)
        lbl = text_img("ヘスペリジン", 76, fill=(255, 255, 255), stroke=10, stroke_fill=(40, 140, 60))
        lx, ly = cx + 150, cy - 300
        paste_center(frame, scaled(lbl, 0.5 + 0.5 * ease_out_back(k)), lx, ly, alpha=clamp(k * 3))
        d.line((lx - 60, ly + 100, cx + 40, cy - 40), fill=(40, 140, 60, int(255 * k)), width=8)
        d.ellipse((cx + 28, cy - 52, cx + 52, cy - 28), fill=(40, 140, 60, int(255 * k)))
        sub = text_img("（ビタミンPとも呼ばれる成分）", 40, fill=(90, 60, 30))
        paste_center(frame, sub, lx - 20, ly + 75, alpha=clamp(k * 3))


def scene_outro(frame, A, t):
    cx, cy = W / 2, 990
    p = ease_out_back(prog(t, 23.0, 0.5), 1.5)
    bob = math.sin((t - 23.0) * 4) * 14
    paste_center(frame, A.shadow, cx, cy + 270, alpha=0.8)
    paste_center(frame, scaled(A.side, 0.5 + 0.5 * p), cx, cy + bob)
    draw_sparkles(frame, A, t, cx, cy, 360, 9, n=8, start=23.0)
    k = ease_out_back(prog(t, 24.0, 0.4))
    if k > 0:
        paste_center(frame, scaled(A.bookmark, 0.3 + 0.7 * k), cx + 330, cy - 280, alpha=clamp(k * 2))


def flash(frame, t, at, dur=0.25):
    if at <= t < at + dur:
        a = 1 - (t - at) / dur
        frame.alpha_composite(Image.new("RGBA", frame.size, (255, 255, 255, int(200 * a))))


def render_frame(A, t):
    frame = A.bg.copy()
    if t < 3.0:
        scene_roll(frame, A, t)
    elif t < 14.0:
        scene_top(frame, A, t)
    elif t < 19.0:
        scene_flower(frame, A, t)
    elif t < 23.0:
        scene_strand(frame, A, t)
    else:
        scene_outro(frame, A, t)
    for at in (3.0, 14.0, 19.0, 23.0):
        flash(frame, t, at)
    paste_center(frame, A.badge, W / 2, 190)
    draw_telop(frame, t)
    draw_subtitle(frame, t)
    return frame.convert("RGB")


# ---------------------------------------------------------------- audio
def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pluck(freq, dur, amp=0.3):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, 8):
        out += (1 / k ** 1.4) * np.sin(2 * np.pi * freq * k * tt) * np.exp(-tt * (3.5 + 1.8 * k))
    out *= np.minimum(1, tt / 0.003)
    return out * amp


def add(buf, sig, at):
    i = int(at * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i]


def make_audio(path):
    total = int(DURATION * SR)
    bgm = np.zeros(total)
    sfx = np.zeros(total)
    bpm = 118
    beat = 60 / bpm
    chords = [  # ウクレレ風（C - G - Am - F）
        ([60, 64, 67, 72], 48),
        ([59, 62, 67, 71], 43),
        ([60, 64, 69, 72], 45),
        ([60, 65, 69, 72], 41),
    ]
    pattern = [(0, 1.0), (1, 0.6), (1.5, 0.45), (2, 0.85), (2.5, 0.45), (3, 0.6), (3.5, 0.45)]
    bar = 0
    t0 = 0.0
    while t0 < DURATION:
        notes, root = chords[bar % 4]
        for pos, vel in pattern:
            at = t0 + pos * beat
            down = int(pos * 2) % 2 == 0
            order = notes if down else notes[::-1]
            for idx, m in enumerate(order):
                add(bgm, pluck(midi_hz(m), 1.2, 0.11 * vel), at + idx * 0.012)
        for pos in (0, 2):
            n = int(beat * 1.6 * SR)
            tt = np.arange(n) / SR
            f = midi_hz(root)
            b = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 3)
            add(bgm, b * 0.22 * np.minimum(1, tt / 0.01), t0 + pos * beat)
        for pos in (0.5, 1.5, 2.5, 3.5):
            n = int(0.05 * SR)
            noise = np.diff(np.random.randn(n + 1)) * np.exp(-np.arange(n) / SR * 90)
            add(bgm, noise * 0.035, t0 + pos * beat)
        # メロディ（シンプルなベル）
        mel = {0: [72, 74, 76, 79], 1: [79, 77, 74, 71], 2: [72, 76, 81, 79], 3: [77, 76, 74, 72]}[bar % 4]
        for i, m in enumerate(mel):
            n = int(0.8 * SR)
            tt = np.arange(n) / SR
            f = midi_hz(m)
            bell = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * f * 3.01 * tt)) * np.exp(-tt * 4)
            add(bgm, bell * 0.05 * np.minimum(1, tt / 0.005), t0 + i * beat)
        t0 += 4 * beat
        bar += 1

    def pop(at, f0=500, f1=1100, amp=0.35):
        n = int(0.09 * SR)
        tt = np.arange(n) / SR
        f = f0 + (f1 - f0) * (tt / tt[-1])
        ph = 2 * np.pi * np.cumsum(f) / SR
        add(sfx, np.sin(ph) * np.exp(-tt * 40) * amp, at)

    def whoosh(at, dur=0.45, amp=0.25):
        n = int(dur * SR)
        noise = np.random.randn(n)
        k = 40
        sm = np.convolve(noise, np.ones(k) / k, mode="same")
        env = np.sin(np.linspace(0, np.pi, n)) ** 2
        add(sfx, sm * env * amp * 3, at)

    def ding(at, amp=0.3):
        for m, d0 in ((84, 0), (88, 0.08), (91, 0.16)):
            n = int(1.0 * SR)
            tt = np.arange(n) / SR
            f = midi_hz(m)
            s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt * 3.5)
            add(sfx, s * amp * 0.5, at + d0)

    def thud(at, amp=0.45):
        n = int(0.25 * SR)
        tt = np.arange(n) / SR
        f = 140 * np.exp(-tt * 12) + 50
        ph = 2 * np.pi * np.cumsum(f) / SR
        add(sfx, np.sin(ph) * np.exp(-tt * 14) * amp, at)

    whoosh(0.0, 1.2, 0.12)
    thud(2.2)
    pop(0.3, 400, 900)
    whoosh(2.95)
    pop(3.4, 400, 900)
    pop(STEM_POP, 300, 1500, 0.45)
    whoosh(7.95)
    for i in range(N_DOTS):
        pop(COUNT_START + i * COUNT_STEP, 600 + 40 * i, 1200 + 60 * i, 0.3)
    ding(13.3)
    whoosh(13.95)
    for i in range(N_DOTS):
        pop(SEG_START + i * SEG_STEP, 350, 700, 0.2)
    ding(15.9, 0.4)
    whoosh(18.95)
    pop(19.4, 400, 900)
    pop(21.0, 500, 1000)
    whoosh(22.95)
    ding(23.3, 0.35)
    pop(24.0, 500, 1300)

    mix = bgm * 0.8 + sfx
    fade = int(1.2 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))
    mix = np.tanh(mix * 1.1) * 0.9
    stereo = np.stack([mix, mix], axis=1)
    pcm = (stereo * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- main
def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "out", "mikan.mp4")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    A = Assets()
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        make_audio(wav)
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", wav,
               "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = int(DURATION * FPS)
        for f in range(frames):
            proc.stdin.write(render_frame(A, f / FPS).tobytes())
            if f % 150 == 0:
                print(f"frame {f}/{frames}", flush=True)
        proc.stdin.close()
        proc.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
