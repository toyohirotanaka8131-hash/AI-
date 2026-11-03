#!/usr/bin/env python3
"""#3 いちご「つぶつぶの正体は…」"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from engine import (OUTRO_LINE, OUTRO_SUB, OUTRO_TELOP, W, Scene, Video, clamp, draw_sparkles, ease_in_out,
                    ease_out_back, ease_out_cubic, label, outro_draw, paste_center, pop_scale, prog, rotated,
                    scaled, soft_shadow, sprite)

random.seed(3)


def berry_mask(w, h):
    """いちごの形（上が丸く、下がとがる）のマスクと正規化座標。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    ny = yy / h                      # 0(上)〜1(下)
    nx = (xx - w / 2) / (w / 2)      # -1〜1
    sh = 0.26   # いちばん幅が広い「肩」の位置
    upper = 0.42 + 0.58 * np.sqrt(np.clip(1 - ((sh - ny) / sh) ** 2, 0, 1))
    lower = np.clip(1 - np.clip((ny - sh) / (1 - sh), 0, 1) ** 1.7, 0, 1) ** 0.8
    hw = np.where(ny < sh, upper, lower)
    inside = (np.abs(nx) <= hw) & (ny >= 0.0)
    return inside, nx, ny, hw


def shade(inside, nx, ny, light_c, base_c, dark_c, hw):
    edge = np.clip(np.abs(nx) / np.maximum(hw, 1e-3), 0, 1)
    lx, ly = -0.35, 0.28
    dl = np.sqrt((nx - lx) ** 2 + ((ny - ly) * 1.8) ** 2)
    t = np.clip(dl / 1.2, 0, 1)[..., None]
    col = np.array(light_c, float) * (1 - t) + np.array(base_c, float) * t
    e = (edge ** 3)[..., None]
    col = col * (1 - 0.5 * e) + np.array(dark_c, float) * 0.5 * e
    sp = np.exp(-(dl ** 2) / 0.02)[..., None]
    col = col * (1 - 0.45 * sp) + 255 * 0.45 * sp
    out = np.zeros(inside.shape + (4,), np.uint8)
    out[..., :3] = col.clip(0, 255)
    out[..., 3] = inside * 255
    return Image.fromarray(out, "RGBA")


def calyx(w):
    def fn(d, k, img):
        c = img.width / 2
        for i in range(7):
            a = math.pi + i * math.pi / 6
            ex, ey = c + math.cos(a) * c * 0.95, img.height * 0.45 - math.sin(a) * img.height * 0.5
            d.polygon([(c - 18 * k, img.height * 0.4), (ex, ey), (c + 18 * k, img.height * 0.4)],
                      fill=(70, 150, 60, 255))
        d.ellipse((c - 30 * k, img.height * 0.22, c + 30 * k, img.height * 0.58), fill=(60, 130, 50, 255))
        d.rounded_rectangle((c - 9 * k, 0, c + 9 * k, img.height * 0.35), radius=int(8 * k), fill=(90, 150, 60, 255))
    return sprite(w, w * 0.42, fn)


def seed_positions(inside, w, h, step):
    pts = []
    for row, y in enumerate(np.arange(h * 0.12, h * 0.93, step)):
        for x in np.arange(step * 0.4 + (step / 2 if row % 2 else 0), w, step):
            if inside[int(y), int(min(w - 1, x))]:
                ny, nx = y / h, (x - w / 2) / (w / 2)
                pts.append((x, y))
    return pts


def make_berry(w, h, seeds_scale=1.0):
    ss = 2
    W2, H2 = w * ss, h * ss
    inside, nx, ny, hw = berry_mask(W2, H2)
    img = shade(inside, nx, ny, (255, 96, 96), (226, 30, 48), (150, 10, 30), hw)
    d = ImageDraw.Draw(img)
    step = 48 * ss * seeds_scale
    seeds = seed_positions(inside, W2, H2, step)
    for x, y in seeds:
        r = 9 * ss * seeds_scale
        d.ellipse((x - r * 1.5, y - r * 1.9, x + r * 1.5, y + r * 1.9), fill=(190, 20, 40, 200))
        d.ellipse((x - r * 0.75, y - r * 1.2, x + r * 0.75, y + r * 1.2), fill=(250, 220, 110, 255))
        d.ellipse((x - r * 0.3, y - r * 0.9, x + r * 0.1, y - r * 0.2), fill=(255, 250, 210, 255))
    img = img.resize((w, h), Image.LANCZOS)
    cal = calyx(int(w * 0.8))
    out = Image.new("RGBA", (w, h + cal.height // 2), (0, 0, 0, 0))
    out.alpha_composite(img, (0, cal.height // 2))
    out.alpha_composite(cal, ((w - cal.width) // 2, 0))
    return out, [(x / ss, y / ss + cal.height // 2) for x, y in seeds]


def make_half(w, h):
    """縦に切った断面。"""
    ss = 2
    W2, H2 = w * ss, h * ss
    inside, nx, ny, hw = berry_mask(W2, H2)
    img = shade(inside, nx, ny, (255, 120, 120), (232, 46, 60), (180, 20, 40), hw)
    arr = np.array(img).astype(float)
    rel = np.abs(nx) / np.maximum(hw, 1e-3)
    inner = inside & (rel < 0.8) & (ny > 0.07) & (ny < 0.9)
    # 内側は白〜ピンクのグラデーション
    t = np.clip(rel / 0.8, 0, 1)[..., None]
    pink = np.array([255, 196, 200], float) * (1 - t) + np.array([240, 84, 98], float) * t
    arr[inner, :3] = pink[inner]
    core = inside & (np.abs(nx) < 0.08 * (1 - ny)) & (ny > 0.12) & (ny < 0.7)
    arr[core, :3] = [255, 236, 236]
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA").filter(ImageFilter.SMOOTH)
    d = ImageDraw.Draw(img)
    for i in range(9):
        yy = H2 * (0.18 + i * 0.075)
        row_hw = np.interp(yy / H2, ny[:, 0], hw[:, int(W2 / 2)])
        for sgn in (-1, 1):
            d.line((W2 / 2 + sgn * W2 * 0.04, yy, W2 / 2 + sgn * W2 / 2 * row_hw * 0.95, yy + 30 * ss),
                   fill=(255, 190, 196, 200), width=int(4 * ss))
    seeds = []
    for i in range(14):
        yy = H2 * (0.1 + i * 0.058)
        row_hw = np.interp(yy / H2, ny[:, 0], hw[:, int(W2 / 2)])
        for sgn in (-1, 1):
            x = W2 / 2 + sgn * (W2 / 2 * row_hw - 6 * ss)
            r = 8 * ss
            d.ellipse((x - r * 0.8, yy - r * 1.2, x + r * 0.8, yy + r * 1.2), fill=(250, 220, 110, 255))
            seeds.append((x / ss, yy / ss))
    img = img.resize((w, h), Image.LANCZOS)
    cal = calyx(int(w * 0.8))
    out = Image.new("RGBA", (w, h + cal.height // 2), (0, 0, 0, 0))
    out.alpha_composite(img, (0, cal.height // 2))
    out.alpha_composite(cal, ((w - cal.width) // 2, 0))
    return out, [(x, y + cal.height // 2) for x, y in seeds]


BERRY, SEEDS = make_berry(440, 520)
BIG_BERRY, BIG_SEEDS = make_berry(760, 900, seeds_scale=1.2)
HALF, HALF_SEEDS = make_half(440, 520)
HALF_L = HALF.transpose(Image.FLIP_LEFT_RIGHT)
SHADOW = soft_shadow(400, 70)


# ---- 水に落ちる
def make_water():
    def fn(d, k, img):
        ww, hh = img.size
        pts = [(x, 30 * k + math.sin(x / (60 * k)) * 12 * k) for x in range(0, ww + 1, int(10 * k))]
        d.polygon(pts + [(ww, hh), (0, hh)], fill=(150, 214, 255, 170))
        d.line(pts, fill=(255, 255, 255, 230), width=int(8 * k))
    return sprite(1080, 560, fn)


WATER = make_water()
DROP = sprite(40, 54, lambda d, k, img: d.ellipse((0, 0, img.width - 1, img.height - 1),
                                                   fill=(200, 236, 255, 230), outline=(255, 255, 255, 255),
                                                   width=int(3 * k)))
BUBBLE = sprite(36, 36, lambda d, k, img: d.ellipse((0, 0, img.width - 1, img.height - 1),
                                                     outline=(255, 255, 255, 220), width=int(4 * k)))
WATER_Y = 1080
IMPACT = 0.85


def scene_drop(frame, lt, sc):
    cx = W / 2
    p = clamp(lt / IMPACT)
    if lt < IMPACT:
        y = -300 + (WATER_Y + 40 + 300) * p * p
        rot = 25 * (1 - p)
    else:
        q = ease_out_cubic(prog(lt, IMPACT, 1.2))
        y = WATER_Y + 40 + 120 * q - 30 * math.sin(q * math.pi)
        rot = 8 * math.sin(lt * 3) * (1 - q * 0.5)
    paste_center(frame, rotated(BERRY, rot), cx, y)
    paste_center(frame, WATER, cx, WATER_Y + 280)
    if lt >= IMPACT:
        rng = random.Random(4)
        for i in range(12):
            q = prog(lt, IMPACT, 0.8)
            if q >= 1:
                break
            a = math.pi + rng.uniform(0.15, math.pi - 0.15)
            v = rng.uniform(380, 620)
            x = cx + math.cos(a) * v * q * 1.2
            yy = WATER_Y + math.sin(a) * v * q + 900 * q * q
            paste_center(frame, scaled(DROP, rng.uniform(0.6, 1.3)), x, yy, alpha=1 - q)
        rng = random.Random(8)
        for i in range(9):
            ph = rng.uniform(0, 1)
            q = ((lt - IMPACT) / 1.6 + ph) % 1.0
            paste_center(frame, scaled(BUBBLE, rng.uniform(0.6, 1.4)), cx + rng.uniform(-300, 300),
                         WATER_Y + 480 - q * 420, alpha=math.sin(q * math.pi) * 0.9)


# ---- 半分に切る
def make_knife():
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((ww * 0.3, 0, ww * 0.7, hh * 0.3), radius=int(16 * k), fill=(120, 72, 40, 255))
        d.polygon([(ww * 0.25, hh * 0.3), (ww * 0.75, hh * 0.3), (ww * 0.75, hh * 0.92), (ww * 0.5, hh)],
                  fill=(214, 220, 228, 255), outline=(150, 160, 170, 255))
    return sprite(90, 620, fn)


KNIFE = make_knife()
CUT = 0.7


def scene_slice(frame, lt, sc):
    cx, cy = W / 2, 1000
    paste_center(frame, SHADOW, cx, cy + 290)
    if lt < CUT + 0.1:
        paste_center(frame, BERRY, cx, cy)
    else:
        gap = ease_out_back(prog(lt, CUT + 0.1, 0.5), 1.4) * 150
        paste_center(frame, HALF_L.crop((0, 0, HALF.width // 2, HALF.height)), cx - HALF.width / 4 - gap, cy)
        paste_center(frame, HALF.crop((HALF.width // 2, 0, HALF.width, HALF.height)), cx + HALF.width / 4 + gap, cy)
    if lt < CUT + 0.4:
        p = ease_in_out(clamp(lt / CUT))
        up = clamp((lt - CUT) / 0.4)
        paste_center(frame, KNIFE, cx, cy - 900 + 760 * p - 600 * up)
    s, a = pop_scale(lt, 2.0)
    if a > 0:
        cross = sprite(260, 260, lambda d, k, img: (d.line((20 * k, 20 * k, 240 * k, 240 * k), fill=(40, 90, 220, 255),
                                                           width=int(34 * k)),
                                                    d.line((240 * k, 20 * k, 20 * k, 240 * k), fill=(40, 90, 220, 255),
                                                           width=int(34 * k))))
        paste_center(frame, scaled(cross, s), cx, cy + 40, alpha=a)


# ---- つぶつぶのアップ
def scene_seeds(frame, lt, sc):
    cx, cy = W / 2, 1040
    z = 0.7 + 0.08 * ease_out_cubic(prog(lt, 0, 0.6))
    img = scaled(BIG_BERRY, z)
    paste_center(frame, img, cx, cy)
    d = ImageDraw.Draw(frame)
    ox, oy = cx - img.width / 2, cy - img.height / 2
    hl = prog(lt, 0.9, 0.4)
    for i, (x, y) in enumerate(BIG_SEEDS):
        ph = (lt * 2.5 - i * 0.07) % 1.0
        r = (14 + 10 * math.sin(ph * math.pi)) * hl
        if r > 0:
            px, py = ox + x * z, oy + y * z
            d.ellipse((px - r, py - r, px + r, py + r), outline=(255, 255, 255, int(200 * hl)), width=4)
    s, a = pop_scale(lt, 1.6)
    if a > 0:
        paste_center(frame, scaled(label("これが実！", 80, fill=(255, 245, 170), stroke_fill=(200, 30, 70)), s),
                     cx + 300, cy + 300, alpha=a)


# ---- ラベルで説明
def arrow(d, x0, y0, x1, y1, color, w=8):
    d.line((x0, y0, x1, y1), fill=color, width=w)
    a = math.atan2(y1 - y0, x1 - x0)
    for s in (2.6, -2.6):
        d.line((x1, y1, x1 + math.cos(a + s) * 30, y1 + math.sin(a + s) * 30), fill=color, width=w)


def scene_labels(frame, lt, sc):
    cx, cy = W / 2 - 120, 1000
    z = 1.1
    img = scaled(HALF, z)
    paste_center(frame, SHADOW, cx, cy + 300)
    paste_center(frame, img, cx, cy)
    ox, oy = cx - img.width / 2, cy - img.height / 2
    d = ImageDraw.Draw(frame)
    k1 = prog(lt, 0.5, 0.35)
    if k1 > 0:
        sx, sy = HALF_SEEDS[9]
        tx, ty = ox + sx * z, oy + sy * z
        arrow(d, 860, 760, tx + 18, ty - 6, (200, 140, 0, int(255 * k1)))
        s, a = pop_scale(lt, 0.5)
        paste_center(frame, scaled(label("実（痩果）", 58, fill=(255, 245, 170), stroke_fill=(160, 100, 0)), s),
                     860, 710, alpha=a)
    k2 = prog(lt, 1.6, 0.35)
    if k2 > 0:
        arrow(d, 860, 1210, cx + 60, cy + 120, (200, 30, 70, int(255 * k2)))
        s, a = pop_scale(lt, 1.6)
        paste_center(frame, scaled(label("花托\n（花の土台）", 56, stroke_fill=(200, 30, 70)), s), 870, 1290, alpha=a)


def outro_subject(frame, cx, cy, s, lt):
    paste_center(frame, SHADOW, cx, cy + 300, alpha=0.8)
    paste_center(frame, scaled(BERRY, s * 1.05), cx, cy)


SCENES = [
    Scene(scene_drop, 3.4, "いちごの「実」は\nどこ？", line="いちごの本当の実って、どこだと思う？",
          sub="いちごの本当の実って、\nどこだと思う？", sfx=[(IMPACT, "splash", {})]),
    Scene(scene_slice, 3.6, "赤いところ…\nじゃない！", line="この赤いところ…実は、違うんだワン！",
          sub="この赤いところ…\n実は、違うんだワン！", sfx=[(CUT, "chop", {}), (2.0, "boing", {"amp": 0.25})]),
    Scene(scene_seeds, 3.6, "正体は\nこのつぶつぶ！", line="本当の実は、表面のつぶつぶ！",
          sub="本当の実は、\n表面のつぶつぶ！", sfx=[(1.6, "ding", {})], jumps=[1.6]),
    Scene(scene_labels, 4.4, "赤い部分は\n花の土台！", line="赤い部分は、花の土台がふくらんだものなんだよ！",
          sub="赤い部分は、花の土台が\nふくらんだものなんだよ！",
          sfx=[(0.5, "pop", {}), (1.6, "pop", {"f0": 450, "f1": 1000})]),
    Scene(outro_draw(outro_subject), 3.0, OUTRO_TELOP, line=OUTRO_LINE, sub=OUTRO_SUB, happy=True,
          jumps=[0.1], sfx=[(0.1, "ding", {"amp": 0.35}), (1.0, "pop", {"f0": 500, "f1": 1300})], tail=0.9),
]

VIDEO = Video(3, SCENES, "ichigo.mp4",
              bg={"top": (255, 245, 247), "bottom": (255, 208, 216), "dot": (240, 90, 120, 28)},
              badge_color=(220, 60, 90), telop_stroke=(200, 30, 70), bubble_color=(230, 80, 110), bgm="sweet",
              bpm=112)

if __name__ == "__main__":
    VIDEO.render()
