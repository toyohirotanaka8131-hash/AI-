#!/usr/bin/env python3
"""#5 トマト「甘いトマトはお尻で見分ける」"""
import math
import random

from PIL import Image, ImageDraw

from engine import (OUTRO_LINE, OUTRO_SUB, OUTRO_TELOP, W, Scene, Video, ball, clamp, draw_sparkles,
                    ease_in_out, ease_out_back, ease_out_cubic, label, outro_draw, paste_center, pop_scale, prog,
                    scaled, soft_shadow, sprite)

RED = ((255, 110, 90), (226, 40, 30), (150, 16, 16))


def make_calyx(size):
    def fn(d, k, img):
        c = size * k / 2
        pts = []
        for i in range(12):
            a = -math.pi / 2 + i * math.pi / 6
            rr = c if i % 2 == 0 else c * 0.3
            pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr * 0.55))
        d.polygon(pts, fill=(60, 140, 50, 255))
        d.rounded_rectangle((c - 9 * k, c - 50 * k, c + 9 * k, c), radius=int(8 * k), fill=(80, 150, 60, 255))
    return sprite(size, size, fn)


def make_tomato(size):
    body = ball(size, *RED, squash=0.82, spec=0.6)
    cal = make_calyx(int(size * 0.46))
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(body)
    out.alpha_composite(cal, (int(size / 2 - cal.width / 2), int(size * 0.1 - cal.height * 0.25)))
    return out


def make_bottom(size, lines=6):
    """お尻側から見たトマト。lines 本の白い放射状の線（スターマーク）。"""
    body = ball(size, *RED, light=(-0.25, -0.3), spec=0.5)
    return body


TOMATO = make_tomato(380)
SMALL = make_tomato(200)
BOTTOM = make_bottom(700)
SHADOW = soft_shadow(330, 60)


# ---- 売り場の棚
def make_shelf():
    def fn(d, k, img):
        ww, hh = img.size
        for y in (0.42, 0.92):
            d.rounded_rectangle((0, hh * y, ww - 1, hh * y + 40 * k), radius=int(10 * k), fill=(200, 150, 96, 255))
            d.rectangle((0, hh * y + 36 * k, ww - 1, hh * y + 52 * k), fill=(160, 110, 66, 255))
    return sprite(1400, 760, fn)


SHELF = make_shelf()
rng = random.Random(5)
SHELF_TOMS = [(i * 170 + rng.uniform(-10, 10), row, rng.uniform(0.85, 1.05)) for row in (0, 1) for i in range(9)]


def scene_shelf(frame, lt, sc):
    cy = 1000
    pan = -120 * ease_in_out(prog(lt, 0, 2.6))
    paste_center(frame, SHELF, W / 2 + 160 + pan, cy)
    top = cy - 380
    for x, row, s in SHELF_TOMS:
        board = top + SHELF.height * (0.42 if row == 0 else 0.92)
        y = board - 84 * s
        paste_center(frame, scaled(SMALL, s), x - 140 + pan + 160, y)
    s, a = pop_scale(lt, 1.4)
    if a > 0:
        paste_center(frame, scaled(label("？", 150, stroke_fill=(190, 30, 20)), s), W / 2 + 150, 640, alpha=a)


# ---- ひっくり返す
FLIP = (0.6, 1.0)


def scene_flip(frame, lt, sc):
    cx, cy = W / 2, 1000
    p = prog(lt, *FLIP)
    paste_center(frame, SHADOW, cx, cy + 260)
    lift = math.sin(p * math.pi) * 120
    if p < 0.5:
        sy = math.cos(p * math.pi)
        paste_center(frame, scaled(TOMATO, 1.2, 1.2 * max(0.02, sy)), cx, cy - lift)
    else:
        sy = -math.cos(p * math.pi)
        img = BOTTOM.copy()
        img = scaled(img, 0.62, 0.62 * 0.82 * max(0.02, sy))
        paste_center(frame, img, cx, cy - lift)
    if lt > 0.1 and p < 1:
        arrow = label("↻", 120, stroke_fill=(190, 30, 20))
        paste_center(frame, arrow, cx + 300, cy - 200, alpha=clamp(lt * 4) * (1 - p))
    s, a = pop_scale(lt, FLIP[0] + FLIP[1] + 0.05)
    if a > 0:
        paste_center(frame, scaled(label("お尻", 90, fill=(255, 245, 170), stroke_fill=(190, 30, 20)), s),
                     cx + 300, cy - 230, alpha=a)


# ---- スターマーク
def scene_star(frame, lt, sc):
    cx, cy = W / 2, 1000
    z = 0.9 + 0.1 * ease_out_cubic(prog(lt, 0, 0.5))
    img = scaled(BOTTOM, z)
    paste_center(frame, img, cx, cy)
    d = ImageDraw.Draw(frame)
    rng = random.Random(9)
    n = 7
    for i in range(n):
        a = -math.pi / 2 + i * 2 * math.pi / n + rng.uniform(-0.15, 0.15)
        L = 300 * z * rng.uniform(0.75, 1.0)
        q = ease_out_cubic(prog(lt, 0.6 + i * 0.12, 0.5))
        if q <= 0:
            continue
        pts = []
        for j in range(21):
            t = j / 20 * q
            r = 20 + L * t
            pts.append((cx + math.cos(a + math.sin(t * 4) * 0.04) * r, cy + math.sin(a + math.sin(t * 4) * 0.04) * r))
        d.line(pts, fill=(255, 240, 230, 235), width=int(12 * z))
    d.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=(160, 110, 50, 255))
    if lt > 1.7:
        draw_sparkles(frame, lt, cx, cy, 340, 4, n=6)
        s, a = pop_scale(lt, 1.7)
        star = label("★", 120, fill=(255, 236, 90), stroke_fill=(200, 120, 0))
        paste_center(frame, scaled(star, s), cx + 330, cy - 300, alpha=a)


# ---- 切ってみる
def make_cross(size):
    def fn(d, k, img):
        S = size * k
        c = S / 2
        d.ellipse((4 * k, 4 * k, S - 4 * k, S - 4 * k), fill=(214, 30, 24, 255))
        d.ellipse((24 * k, 24 * k, S - 24 * k, S - 24 * k), fill=(240, 80, 64, 255))
        for i in range(4):
            a = i * math.pi / 2 + math.pi / 4
            px, py = c + math.cos(a) * S * 0.24, c + math.sin(a) * S * 0.24
            rx, ry = S * 0.17, S * 0.13
            box = (px - rx, py - ry, px + rx, py + ry)
            loc = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(loc)
            ld.ellipse(box, fill=(220, 214, 90, 255))
            loc = loc.rotate(-math.degrees(a), center=(px, py))
            img.alpha_composite(loc)
            r2 = random.Random(i)
            for j in range(7):
                sa = a + r2.uniform(-0.7, 0.7)
                sr = S * r2.uniform(0.17, 0.3)
                sx, sy = c + math.cos(sa) * sr, c + math.sin(sa) * sr
                d.ellipse((sx - 7 * k, sy - 10 * k, sx + 7 * k, sy + 10 * k), fill=(250, 240, 200, 255))
        d.ellipse((c - S * 0.09, c - S * 0.09, c + S * 0.09, c + S * 0.09), fill=(250, 120, 100, 255))
    return sprite(size, size, fn)


CROSS = make_cross(560)


def scene_cut(frame, lt, sc):
    cx, cy = W / 2, 1000
    p = ease_out_back(prog(lt, 0.1, 0.5), 1.5)
    paste_center(frame, SHADOW, cx, cy + 300)
    paste_center(frame, scaled(CROSS, 0.5 + 0.5 * p), cx, cy)
    s, a = pop_scale(lt, 1.0)
    if a > 0:
        paste_center(frame, scaled(label("ゼリーたっぷり", 64, fill=(255, 250, 200), stroke_fill=(120, 140, 20)), s),
                     cx, cy + 370, alpha=a)
    if lt > 1.8:
        draw_sparkles(frame, lt, cx, cy, 330, 8, n=6)


# ---- 締め：塩をふって
def make_plate():
    def fn(d, k, img):
        d.ellipse((0, 0, img.width - 1, img.height - 1), fill=(255, 255, 255, 255), outline=(220, 210, 200, 255),
                  width=int(4 * k))
        d.ellipse((img.width * 0.1, img.height * 0.12, img.width * 0.9, img.height * 0.88),
                  outline=(236, 230, 222, 255), width=int(4 * k))
    return sprite(700, 440, fn)


PLATE = make_plate()
SLICE = scaled(CROSS, 0.34)


def outro_subject(frame, cx, cy, s, lt):
    paste_center(frame, scaled(PLATE, s), cx, cy + 60)
    for i, dx in enumerate((-170, 0, 170)):
        paste_center(frame, scaled(SLICE, s, s * 0.7), cx + dx * s, cy + 40 * s)
    d = ImageDraw.Draw(frame)
    r = random.Random(1)
    for i in range(40):
        ph = r.uniform(0, 1)
        q = ((lt / 1.2) + ph) % 1.0
        x = cx + r.uniform(-200, 200)
        y = cy - 380 + q * 400
        d.rectangle((x - 3, y - 3, x + 3, y + 3), fill=(255, 255, 255, int(255 * math.sin(q * math.pi))))


SCENES = [
    Scene(scene_shelf, 3.0, "甘いトマト、\nどれ？", line="甘いトマトの見分け方、知ってる？",
          sub="甘いトマトの見分け方、\n知ってる？", sfx=[(1.4, "pop", {})]),
    Scene(scene_flip, 3.2, "見るのは\nお尻！", line="見るのは、ひっくり返したお尻！",
          sub="見るのは、\nひっくり返したお尻！",
          sfx=[(FLIP[0], "whoosh", {}), (FLIP[0] + FLIP[1], "thud", {}), (1.65, "pop", {})], jumps=[1.65]),
    Scene(scene_star, 3.8, "白い線\n「スターマーク」", line="白い線が、星みたいに出ているもの…",
          sub="白い線が、星みたいに\n出ているもの…",
          sfx=[(0.6 + i * 0.12, "pop", {"f0": 700 + 60 * i, "f1": 1300 + 60 * i, "amp": 0.12}) for i in range(7)]
          + [(1.7, "ding", {})]),
    Scene(scene_cut, 4.0, "甘いことが\n多いと言われる！", line="これが、甘いことが多いって、言われているんだワン！",
          sub="これが、甘いことが多いって\n言われているんだワン！",
          sfx=[(0.1, "chop", {}), (1.0, "pop", {})], jumps=[1.0]),
    Scene(outro_draw(outro_subject), 3.0, OUTRO_TELOP, line=OUTRO_LINE, sub=OUTRO_SUB, happy=True,
          jumps=[0.1], sfx=[(0.1, "ding", {"amp": 0.35}), (0.4, "shake", {"dur": 1.5, "amp": 0.06}),
                            (1.0, "pop", {"f0": 500, "f1": 1300})], tail=0.9),
]

VIDEO = Video(5, SCENES, "tomato.mp4",
              bg={"top": (255, 247, 240), "bottom": (255, 206, 186), "dot": (230, 80, 50, 26)},
              badge_color=(214, 60, 40), telop_stroke=(190, 30, 20), bubble_color=(220, 80, 60), bgm="fresh",
              bpm=116)

if __name__ == "__main__":
    VIDEO.render()
