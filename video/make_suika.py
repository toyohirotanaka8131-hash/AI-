#!/usr/bin/env python3
"""#10 スイカ「スイカに塩をかけるのはなぜ？」"""
import math
import random

from PIL import Image, ImageDraw

from engine import (OUTRO_LINE, OUTRO_SUB, OUTRO_TELOP, W, Scene, Video, clamp, draw_sparkles, ease_in_out,
                    ease_out_back, ease_out_cubic, label, outro_draw, paste_center, pop_scale, prog, rotated,
                    scaled, soft_shadow, sprite)

RIND, RIND_D, WHITE, RED, RED_L = (60, 150, 60), (30, 90, 40), (236, 246, 214), (236, 50, 70), (255, 110, 120)


def make_slice(w):
    """三角の一切れ（下が皮）。"""
    h = int(w * 0.8)

    def fn(d, k, img):
        ww, hh = img.size
        cx = ww / 2
        R = hh * 1.05
        top = (cx, 0)
        a = math.radians(32)

        def arc(r):
            return [(cx + math.sin(t) * r, math.cos(t) * r) for t in [-a + 2 * a * i / 40 for i in range(41)]]
        d.polygon([top] + arc(R), fill=RIND + (255,))
        d.polygon([top] + arc(R * 0.95), fill=WHITE + (255,))
        d.polygon([top] + arc(R * 0.9), fill=RED + (255,))
        d.polygon([top] + arc(R * 0.55), fill=RED_L + (120,))
        for t, rr in [(-0.25, 0.35), (0.2, 0.42), (-0.1, 0.6), (0.3, 0.68), (-0.35, 0.72), (0.05, 0.8),
                      (-0.2, 0.84), (0.25, 0.82)]:
            x, y = cx + math.sin(t * a * 2.4) * R * rr, math.cos(t * a * 2.4) * R * rr
            d.ellipse((x - 8 * k, y - 13 * k, x + 8 * k, y + 13 * k), fill=(30, 20, 20, 255))
            d.ellipse((x - 3 * k, y - 9 * k, x + 1 * k, y - 3 * k), fill=(120, 110, 110, 255))
    return sprite(w, h, fn)


SLICE = make_slice(620)
SHADOW = soft_shadow(520, 70)


def make_shaker():
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((ww * 0.1, hh * 0.25, ww * 0.9, hh - 1), radius=int(30 * k), fill=(240, 248, 255, 230),
                            outline=(180, 200, 220, 255), width=int(5 * k))
        d.rounded_rectangle((ww * 0.16, hh * 0.5, ww * 0.84, hh * 0.95), radius=int(20 * k), fill=(255, 255, 255, 255))
        d.rounded_rectangle((ww * 0.06, 0, ww * 0.94, hh * 0.28), radius=int(26 * k), fill=(190, 196, 206, 255))
        for i in range(3):
            x = ww * (0.32 + i * 0.18)
            d.ellipse((x - 6 * k, hh * 0.08, x + 6 * k, hh * 0.08 + 12 * k), fill=(110, 116, 126, 255))
    return sprite(160, 240, fn)


SHAKER = make_shaker()


def salt_particles(frame, lt, sx, sy, spread=120, n=30, start=0.0):
    d = ImageDraw.Draw(frame)
    r = random.Random(1)
    for i in range(n):
        ph = r.uniform(0, 1)
        q = ((lt - start) / 0.9 + ph) % 1.0
        x = sx + r.uniform(-spread, spread) * q
        y = sy + q * 380
        d.rectangle((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255, int(255 * (1 - q))),
                    outline=(200, 210, 220, int(200 * (1 - q))))


def scene_hook(frame, lt, sc):
    cx, cy = W / 2 - 80, 1060
    paste_center(frame, SHADOW, cx, cy + 270)
    paste_center(frame, SLICE, cx, cy)
    tilt = math.sin(lt * 10) * 10 if lt > 0.6 else 0
    paste_center(frame, rotated(SHAKER, 150 + tilt), cx + 300, cy - 330)
    if lt > 0.6:
        salt_particles(frame, lt, cx + 250, cy - 270, n=16, start=0.6)
    s, a = pop_scale(lt, 1.4)
    if a > 0:
        paste_center(frame, scaled(label("なぜ？", 100, stroke_fill=(30, 110, 40)), s), cx - 260, cy - 330, alpha=a)


def make_meter(h):
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((0, 0, ww - 1, hh - 1), radius=int(ww / 2), fill=(255, 255, 255, 255),
                            outline=(210, 200, 190, 255), width=int(5 * k))
    return sprite(90, h, fn)


METER = make_meter(560)


def scene_salt(frame, lt, sc):
    cx, cy = W / 2 - 110, 1070
    paste_center(frame, SHADOW, cx, cy + 270)
    paste_center(frame, SLICE, cx, cy)
    tilt = math.sin(lt * 10) * 12 if lt < 1.6 else 0
    paste_center(frame, rotated(SHAKER, 160 + tilt), cx, cy - 400)
    paste_center(frame, label("しお", 50, stroke_fill=(110, 120, 140), stroke=7), cx - 170, cy - 420)
    if lt < 2.0:
        salt_particles(frame, lt, cx, cy - 330, spread=180, n=40)
    # 甘さメーター
    mx, my = 930, 1040
    paste_center(frame, METER, mx, my)
    fill = 0.45 + 0.45 * ease_in_out(prog(lt, 0.6, 1.4))
    d = ImageDraw.Draw(frame)
    top = my + 270 - 540 * fill
    d.rounded_rectangle((mx - 32, top, mx + 32, my + 270), radius=30, fill=(236, 70, 90))
    paste_center(frame, label("甘さ", 50, stroke_fill=(200, 40, 60), stroke=7), mx, my + 330)
    s, a = pop_scale(lt, 2.1)
    if a > 0:
        paste_center(frame, scaled(label("UP！", 80, fill=(255, 250, 200), stroke_fill=(200, 40, 60)), s), mx - 60,
                     top - 60, alpha=a)
        paste_center(frame, scaled(label("対比効果", 70, stroke_fill=(30, 110, 40)), s), cx, cy + 290, alpha=a)


def make_round(size, cuts=0):
    def fn(d, k, img):
        S = size * k
        c = S / 2

        def circ(r, col):
            d.ellipse((c - r, c - r, c + r, c + r), fill=col)
        circ(S * 0.5 - 2, RIND + (255,))
        circ(S * 0.47, WHITE + (255,))
        circ(S * 0.44, RED + (255,))
        r = random.Random(4)
        for i in range(36):
            a = r.uniform(0, 2 * math.pi)
            rr = S * r.uniform(0.12, 0.38)
            x, y = c + math.cos(a) * rr, c + math.sin(a) * rr
            d.ellipse((x - 6 * k, y - 10 * k, x + 6 * k, y + 10 * k), fill=(30, 20, 20, 255))
    return sprite(size, size, fn)


ROUND = make_round(640)
GLOW = sprite(400, 400, lambda d, k, img: [d.ellipse((img.width / 2 - r, img.height / 2 - r, img.width / 2 + r,
                                                       img.height / 2 + r), fill=(255, 240, 160, 26))
                                           for r in [img.width * 0.5 * i / 10 for i in range(10, 0, -1)]])


def scene_center(frame, lt, sc):
    cx, cy = W / 2, 930
    p = ease_out_back(prog(lt, 0, 0.5), 1.4)
    paste_center(frame, soft_shadow(540, 80), cx, cy + 330)
    paste_center(frame, scaled(ROUND, 0.6 + 0.4 * p), cx, cy)
    g = prog(lt, 0.8, 0.5)
    if g > 0:
        pulse = 1 + 0.06 * math.sin(lt * 5)
        paste_center(frame, scaled(GLOW, pulse), cx, cy, alpha=g)
        draw_sparkles(frame, lt, cx, cy, 120, 5, n=5)
        s, a = pop_scale(lt, 0.8)
        paste_center(frame, scaled(label("ここがいちばん甘い", 60, fill=(255, 255, 255), stroke_fill=(200, 40, 60)), s),
                     cx, cy + 365, alpha=a)


def scene_cut(frame, lt, sc):
    cx, cy = W / 2, 930
    paste_center(frame, soft_shadow(540, 80), cx, cy + 330)
    paste_center(frame, ROUND, cx, cy)
    d = ImageDraw.Draw(frame)
    n = 8
    for i in range(n):
        q = ease_out_cubic(prog(lt, 0.3 + i * 0.18, 0.3))
        if q <= 0:
            continue
        a = -math.pi / 2 + i * 2 * math.pi / n
        d.line((cx, cy, cx + math.cos(a) * 320 * q, cy + math.sin(a) * 320 * q), fill=(255, 255, 255), width=10)
    if lt > 1.9:
        paste_center(frame, scaled(GLOW, 0.6), cx, cy, alpha=0.8)
        s, a = pop_scale(lt, 1.9)
        paste_center(frame, scaled(label("みんな甘い！", 80, fill=(255, 250, 200), stroke_fill=(200, 40, 60)), s),
                     cx, cy + 370, alpha=a)
        draw_sparkles(frame, lt, cx, cy, 340, 7, n=8)


def outro_subject(frame, cx, cy, s, lt):
    paste_center(frame, SHADOW, cx, cy + 260, alpha=0.8)
    paste_center(frame, scaled(SLICE, s * 0.95), cx, cy)


SCENES = [
    Scene(scene_hook, 3.0, "スイカに塩、\nなぜかける？", line="スイカに塩をかけるのは、なぜだと思う？",
          sub="スイカに塩をかけるのは、\nなぜだと思う？", sfx=[(0.6, "shake", {"dur": 1.2}), (1.4, "pop", {})]),
    Scene(scene_salt, 4.2, "塩で甘さが\n引き立つ！",
          line="少しの塩で、甘さがより強く感じられるんだワン！これを、対比効果っていうよ！",
          sub="少しの塩で、甘さがより強く\n感じられるんだワン！これを\n対比効果っていうよ！",
          sfx=[(0.0, "shake", {"dur": 1.6}), (2.1, "ding", {})], jumps=[2.1]),
    Scene(scene_center, 3.8, "いちばん甘いのは\n真ん中！", line="それから、スイカは、真ん中がいちばん甘いんだって！",
          sub="それから、スイカは、\n真ん中がいちばん甘いんだって！", sfx=[(0.8, "ding", {})]),
    Scene(scene_cut, 4.0, "放射状に切れば\nみんな甘い", line="放射状に切り分ければ、みんなに甘いところが、行きわたるよ！",
          sub="放射状に切り分ければ、\nみんなに甘いところが、\n行きわたるよ！",
          sfx=[(0.3 + i * 0.18, "chop", {"amp": 0.25}) for i in range(8)] + [(1.9, "ding", {})], jumps=[1.9]),
    Scene(outro_draw(outro_subject), 3.0, OUTRO_TELOP, line=OUTRO_LINE, sub=OUTRO_SUB, happy=True,
          jumps=[0.1], sfx=[(0.1, "ding", {"amp": 0.35}), (1.0, "pop", {"f0": 500, "f1": 1300})], tail=0.9),
]

VIDEO = Video(10, SCENES, "suika.mp4",
              bg={"top": (244, 252, 240), "bottom": (255, 214, 214), "dot": (60, 150, 60, 24)},
              badge_color=(50, 140, 60), telop_stroke=(30, 110, 40), bubble_color=(60, 150, 70), bgm="sweet",
              bpm=120)

THUMB = ("スイカに塩、\nなぜかける？", (255, 150, 150))


def thumb_subject(f):
    paste_center(f, SHADOW, W / 2 - 40, 1350)
    paste_center(f, scaled(SLICE, 1.1), W / 2 - 40, 1100)
    paste_center(f, rotated(scaled(SHAKER, 1.2), 150), W / 2 + 330, 900)
    salt_particles(f, 0.5, W / 2 + 270, 960, n=20)


if __name__ == "__main__":
    VIDEO.render()
