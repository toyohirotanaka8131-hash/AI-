#!/usr/bin/env python3
"""#7 にんじん「にんじんの皮、むいてる？」"""
import math
import random

from PIL import Image, ImageDraw

from engine import (OUTRO_LINE, OUTRO_SUB, OUTRO_TELOP, W, Scene, Video, clamp, draw_sparkles, ease_in_out,
                    ease_out_back, ease_out_cubic, label, outro_draw, paste_center, pop_scale, prog, rotated,
                    scaled, soft_shadow, sprite)

ORANGE_L, ORANGE, ORANGE_D = (255, 170, 70), (244, 120, 20), (200, 80, 10)


def make_carrot(w, h, skin=False):
    def fn(d, k, img):
        ww, hh = img.size
        c = ww / 2
        top = hh * 0.22
        body = []
        for i in range(41):
            t = i / 40
            y = top + (hh - top - 8 * k) * t
            half = ww * 0.36 * (1 - t) ** 0.9 + 4 * k
            body.append((c + half, y))
        left = [(2 * c - x, y) for x, y in body]
        poly = body + left[::-1]
        d.polygon(poly, fill=(ORANGE_D if skin else ORANGE) + (255,))
        # つや
        d.line([(c - ww * 0.18 * (1 - i / 30) ** 0.9, top + (hh - top) * 0.85 * i / 30) for i in range(31)],
               fill=ORANGE_L + (255,), width=int(12 * k))
        rng = random.Random(1)
        for i in range(9):
            y = top + (hh - top) * (0.1 + i * 0.09)
            t = (y - top) / (hh - top)
            half = ww * 0.36 * (1 - t) ** 0.9
            x0 = c + rng.uniform(-half * 0.8, 0)
            d.line((x0, y, x0 + half * rng.uniform(0.5, 0.9), y + 4 * k), fill=(190, 80, 10, 180),
                   width=int(4 * k))
        # 葉
        for a, l in ((-25, 0.9), (0, 1.0), (25, 0.9), (-50, 0.7), (50, 0.7)):
            r = math.radians(a)
            ex, ey = c + math.sin(r) * ww * 0.5 * l, top - math.cos(r) * hh * 0.2 * l
            d.line((c, top + 6 * k, ex, ey), fill=(70, 150, 60, 255), width=int(12 * k))
            d.ellipse((ex - 26 * k, ey - 18 * k, ex + 26 * k, ey + 18 * k), fill=(90, 170, 70, 255))
    return sprite(w, h, fn)


CARROT = make_carrot(300, 820)
CARROT_SKIN = make_carrot(300, 820, skin=True)
SHADOW = soft_shadow(300, 60)


def make_peeler():
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((ww * 0.38, hh * 0.35, ww * 0.62, hh - 1), radius=int(18 * k), fill=(90, 160, 220, 255))
        d.rounded_rectangle((0, 0, ww - 1, hh * 0.4), radius=int(30 * k), outline=(150, 160, 170, 255),
                            width=int(14 * k))
        d.line((20 * k, hh * 0.2, ww - 20 * k, hh * 0.2), fill=(200, 206, 214, 255), width=int(10 * k))
    return sprite(200, 380, fn)


PEELER = make_peeler()


def scene_hook(frame, lt, sc):
    cx, cy = W / 2 - 60, 1000
    paste_center(frame, SHADOW, cx, cy + 420)
    paste_center(frame, rotated(CARROT, -12), cx, cy)
    sway = math.sin(lt * 5) * 20
    paste_center(frame, rotated(PEELER, 30 + sway * 0.3), cx + 260, cy - 60 + sway)
    s, a = pop_scale(lt, 1.2)
    if a > 0:
        paste_center(frame, scaled(label("？", 150, stroke_fill=(200, 80, 10)), s), cx + 360, cy - 330, alpha=a)


# ---- 洗浄
DROP = sprite(26, 40, lambda d, k, img: d.ellipse((0, 0, img.width - 1, img.height - 1), fill=(150, 210, 255, 220)))
FLAKE = sprite(60, 22, lambda d, k, img: d.ellipse((0, 0, img.width - 1, img.height - 1), fill=ORANGE_D + (230,)))


def make_brush():
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((0, 0, ww - 1, hh * 0.4), radius=int(20 * k), fill=(90, 160, 220, 255))
        for i in range(12):
            x = 16 * k + i * (ww - 32 * k) / 11
            d.line((x, hh * 0.4, x, hh - 1), fill=(240, 240, 240, 255), width=int(6 * k))
    return sprite(260, 120, fn)


BRUSH = make_brush()


def scene_wash(frame, lt, sc):
    cx, cy = W / 2, 1010
    car = rotated(CARROT, 90)
    skin = rotated(CARROT_SKIN, 90)
    clean = ease_in_out(prog(lt, 0.4, 2.4))
    paste_center(frame, car, cx, cy)
    paste_center(frame, skin, cx, cy, alpha=1 - clean)
    # ブラシが左右に動く
    bx = cx + math.sin(lt * 7) * 240
    paste_center(frame, BRUSH, bx, cy - 190)
    paste_center(frame, BRUSH.transpose(Image.FLIP_TOP_BOTTOM), bx - 80, cy + 190)
    rng = random.Random(3)
    for i in range(26):
        ph = rng.uniform(0, 1)
        q = ((lt / 0.8) + ph) % 1.0
        x = cx + rng.uniform(-420, 420)
        paste_center(frame, DROP, x, cy - 480 + q * 420, alpha=0.9 * math.sin(q * math.pi))
    if lt < 3.0:
        for i in range(10):
            ph = rng.uniform(0, 1)
            q = ((lt / 1.1) + ph) % 1.0
            x = cx + rng.uniform(-380, 380)
            paste_center(frame, rotated(FLAKE, q * 300), x + q * 40, cy + 40 + q * 360,
                         alpha=(1 - q) * (1 - clean * 0.7))
    if lt > 2.8:
        s, a = pop_scale(lt, 2.8)
        paste_center(frame, scaled(label("ピカピカ！", 70, fill=(255, 250, 200), stroke_fill=(200, 80, 10)), s),
                     cx + 220, cy + 330, alpha=a)
        draw_sparkles(frame, lt, cx, cy, 380, 4, n=6)


# ---- 断面とβカロテン
def make_section(size):
    def fn(d, k, img):
        S = size * k
        c = S / 2

        def circ(r, col):
            d.ellipse((c - r, c - r, c + r, c + r), fill=col)
        circ(S * 0.5 - 2 * k, (214, 90, 10, 255))
        circ(S * 0.47, (255, 136, 30, 255))
        circ(S * 0.27, (255, 190, 90, 255))
        for i in range(12):
            a = i * math.pi / 6
            d.line((c, c, c + math.cos(a) * S * 0.25, c + math.sin(a) * S * 0.25), fill=(255, 206, 120, 255),
                   width=int(3 * k))
        circ(S * 0.05, (255, 214, 140, 255))
    return sprite(size, size, fn)


SECTION = make_section(620)


def scene_carotene(frame, lt, sc):
    cx, cy = W / 2 - 60, 960
    p = ease_out_back(prog(lt, 0, 0.5), 1.5)
    paste_center(frame, soft_shadow(440, 70), cx, cy + 270)
    paste_center(frame, scaled(SECTION, (0.5 + 0.5 * p) * 0.82), cx, cy)
    k = prog(lt, 0.8, 0.4)
    if k > 0:
        d = ImageDraw.Draw(frame)
        pulse = 6 + 4 * math.sin(lt * 6)
        r = 250
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, int(220 * k)), width=int(pulse))
        d.line((cx + 200, cy - 150, cx + 330, cy - 230), fill=(200, 80, 10, int(255 * k)), width=8)
        s, a = pop_scale(lt, 0.8)
        paste_center(frame, scaled(label("βカロテン\nたっぷり", 60, fill=(255, 250, 200), stroke_fill=(200, 80, 10)),
                                   s), cx + 380, cy - 320, alpha=a)
    s, a = pop_scale(lt, 2.0)
    if a > 0:
        paste_center(frame, scaled(label("洗うだけでOK", 70, stroke_fill=(40, 130, 200)), s), cx + 120, cy + 330,
                     alpha=a)


# ---- 油と一緒に
def make_pan():
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((ww * 0.72, hh * 0.42, ww - 1, hh * 0.58), radius=int(20 * k), fill=(60, 50, 46, 255))
        d.ellipse((0, 0, ww * 0.78, hh - 1), fill=(70, 66, 64, 255))
        d.ellipse((ww * 0.04, hh * 0.08, ww * 0.74, hh * 0.92), fill=(46, 44, 44, 255))
    return sprite(900, 440, fn)


PAN = make_pan()
STICK = sprite(200, 40, lambda d, k, img: (d.rounded_rectangle((0, 0, img.width - 1, img.height - 1),
                                                               radius=int(12 * k), fill=ORANGE + (255,)),
                                           d.line((10 * k, 12 * k, img.width - 10 * k, 12 * k),
                                                  fill=ORANGE_L + (255,), width=int(6 * k))))
OIL = sprite(90, 120, lambda d, k, img: (d.polygon([(img.width / 2, 0), (img.width - 8 * k, img.height * 0.62),
                                                    (8 * k, img.height * 0.62)], fill=(250, 214, 60, 255)),
                                         d.ellipse((6 * k, img.height * 0.3, img.width - 6 * k, img.height - 1),
                                                   fill=(250, 214, 60, 255)),
                                         d.ellipse((img.width * 0.28, img.height * 0.5, img.width * 0.45,
                                                    img.height * 0.66), fill=(255, 250, 220, 255))))


def scene_oil(frame, lt, sc):
    cx, cy = W / 2, 1000
    paste_center(frame, PAN, cx + 60, cy)
    rng = random.Random(5)
    for i in range(9):
        x = cx - 180 + (i % 3) * 130 + rng.uniform(-20, 20)
        y = cy - 90 + (i // 3) * 80 + rng.uniform(-10, 10)
        jump = abs(math.sin(lt * 6 + i)) * 18 * (lt > 0.4)
        paste_center(frame, rotated(STICK, rng.uniform(-30, 30)), x, y - jump)
    p = prog(lt, 0.2, 0.6)
    if p < 1:
        paste_center(frame, OIL, cx - 40, cy - 520 + 420 * p * p, alpha=1 - prog(lt, 0.7, 0.1))
    for i in range(6):
        ph = rng.uniform(0, 1)
        q = ((lt / 0.9) + ph) % 1.0
        x = cx - 250 + rng.uniform(0, 500)
        r = 10 + 8 * math.sin(q * math.pi)
        d = ImageDraw.Draw(frame)
        d.ellipse((x - r, cy - 120 - q * 160 - r, x + r, cy - 120 - q * 160 + r),
                  outline=(255, 255, 255, int(200 * math.sin(q * math.pi))), width=3)
    s, a = pop_scale(lt, 1.2)
    if a > 0:
        paste_center(frame, scaled(label("吸収アップ！", 76, fill=(255, 250, 200), stroke_fill=(200, 80, 10)), s),
                     cx + 120, cy + 300, alpha=a)


def outro_subject(frame, cx, cy, s, lt):
    paste_center(frame, SHADOW, cx, cy + 400, alpha=0.8)
    paste_center(frame, rotated(scaled(CARROT, s * 0.95), -10), cx, cy)


SCENES = [
    Scene(scene_hook, 3.0, "にんじんの皮、\nむいてる？", line="にんじんの皮、むいてる？",
          sub="にんじんの皮、\nむいてる？", sfx=[(1.2, "pop", {})]),
    Scene(scene_wash, 4.0, "実は皮は\nほぼむけてる！",
          line="実は、お店のにんじんは、出荷前の洗浄で、皮がほとんどむけているんだワン！",
          sub="実は、お店のにんじんは、\n出荷前の洗浄で、皮が\nほとんどむけているんだワン！",
          sfx=[(0.2, "shake", {"dur": 2.6, "amp": 0.08}), (2.8, "ding", {})], jumps=[2.8]),
    Scene(scene_carotene, 4.0, "皮の近くに\n栄養たっぷり", line="皮の近くには、ベータカロテンがたっぷり。洗うだけでオッケー！",
          sub="皮の近くには、βカロテンが\nたっぷり。\n洗うだけでオッケー！",
          sfx=[(0.8, "pop", {}), (2.0, "pop", {"f0": 500, "f1": 1300})]),
    Scene(scene_oil, 3.6, "油と一緒で\n吸収アップ", line="油と一緒に食べると、吸収がよくなるよ！",
          sub="油と一緒に食べると、\n吸収がよくなるよ！",
          sfx=[(0.8, "splash", {"amp": 0.2}), (1.2, "ding", {})], jumps=[1.2]),
    Scene(outro_draw(outro_subject), 3.0, OUTRO_TELOP, line=OUTRO_LINE, sub=OUTRO_SUB, happy=True,
          jumps=[0.1], sfx=[(0.1, "ding", {"amp": 0.35}), (1.0, "pop", {"f0": 500, "f1": 1300})], tail=0.9),
]

VIDEO = Video(7, SCENES, "ninjin.mp4",
              bg={"top": (255, 249, 236), "bottom": (255, 216, 170), "dot": (244, 120, 20, 26)},
              badge_color=(236, 110, 20), telop_stroke=(200, 80, 10), bubble_color=(236, 128, 30), bgm="fresh",
              bpm=120)

THUMB = ("にんじんの皮\nむいてる？", (255, 170, 80))


def thumb_subject(f):
    paste_center(f, SHADOW, W / 2 + 120, 1460)
    paste_center(f, rotated(scaled(CARROT, 0.85), -14), W / 2 + 150, 1130)
    paste_center(f, rotated(PEELER, 30), W / 2 - 250, 1020)
    paste_center(f, label("✕", 170, fill=(255, 255, 255), stroke_fill=(40, 90, 220), stroke=14), W / 2 - 250, 1000)


if __name__ == "__main__":
    VIDEO.render()
