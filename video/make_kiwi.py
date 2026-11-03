#!/usr/bin/env python3
"""#8 キウイ「キウイでお肉がやわらかくなる」"""
import math
import random

from PIL import Image, ImageDraw

from engine import (OUTRO_LINE, OUTRO_SUB, OUTRO_TELOP, W, Scene, Video, ball, clamp, draw_sparkles,
                    ease_out_back, ease_out_cubic, label, outro_draw, paste_center, pop_scale, prog, rotated,
                    scaled, soft_shadow, sprite)


def make_kiwi(size):
    body = ball(size, (190, 150, 100), (150, 106, 60), (96, 64, 34), squash=0.78, spec=0.15)
    d = ImageDraw.Draw(body)
    rng = random.Random(8)
    a = body.getchannel("A")
    for _ in range(1600):
        x, y = rng.uniform(0, size - 1), rng.uniform(0, size - 1)
        if a.getpixel((int(x), int(y))) < 200:
            continue
        d.line((x, y, x + rng.uniform(-4, 4), y + rng.uniform(2, 6)), fill=(110, 76, 40, 160), width=2)
    return body


def make_half(size):
    def fn(d, k, img):
        S = size * k
        c = S / 2
        d.ellipse((0, S * 0.1, S - 1, S * 0.9), fill=(120, 84, 44, 255))
        d.ellipse((8 * k, S * 0.1 + 8 * k, S - 8 * k, S * 0.9 - 8 * k), fill=(110, 170, 40, 255))
        d.ellipse((S * 0.12, S * 0.22, S * 0.88, S * 0.78), fill=(150, 200, 60, 255))
        for i in range(28):
            a = i * 2 * math.pi / 28
            d.line((c, c, c + math.cos(a) * S * 0.36, c + math.sin(a) * S * 0.27), fill=(196, 226, 120, 255),
                   width=int(3 * k))
        d.ellipse((c - S * 0.16, c - S * 0.1, c + S * 0.16, c + S * 0.1), fill=(240, 246, 210, 255))
        rng = random.Random(2)
        for i in range(40):
            a = i * 2 * math.pi / 40 + rng.uniform(-0.05, 0.05)
            r = rng.uniform(0.2, 0.25)
            x, y = c + math.cos(a) * S * r, c + math.sin(a) * S * r * 0.72
            d.ellipse((x - 5 * k, y - 8 * k, x + 5 * k, y + 8 * k), fill=(30, 24, 16, 255))
    return sprite(size, size, fn)


KIWI = make_kiwi(360)
HALF = make_half(520)
SHADOW = soft_shadow(340, 60)


def make_steak(w, h, soft=0.0):
    def fn(d, k, img):
        ww, hh = img.size
        pts = []
        for i in range(36):
            a = i * 2 * math.pi / 36
            r = 1 + 0.08 * math.sin(a * 3) + 0.05 * math.cos(a * 5)
            pts.append((ww / 2 + math.cos(a) * ww * 0.46 * r, hh / 2 + math.sin(a) * hh * 0.42 * r))
        col = (int(150 + 40 * soft), int(70 + 30 * soft), int(56 + 26 * soft))
        d.polygon(pts, fill=col + (255,))
        d.line(pts + [pts[0]], fill=(250, 236, 220, 255), width=int(16 * k))
        for i in range(4):
            x = ww * (0.25 + i * 0.16)
            d.line((x, hh * 0.22, x + ww * 0.12, hh * 0.78), fill=(90, 40, 30, 200), width=int(10 * k))
    return sprite(w, h, fn)


STEAK = make_steak(560, 360)
STEAK_SOFT = make_steak(560, 360, soft=1.0)


def scene_hook(frame, lt, sc):
    cx, cy = W / 2, 1020
    paste_center(frame, soft_shadow(520, 80), cx + 120, cy + 170)
    paste_center(frame, STEAK, cx + 120, cy + 40)
    p = ease_out_back(prog(lt, 0.2, 0.5), 1.6)
    paste_center(frame, rotated(scaled(KIWI, 0.4 + 0.6 * p), math.sin(lt * 3) * 6), cx - 220, cy - 160)
    s, a = pop_scale(lt, 1.3)
    if a > 0:
        paste_center(frame, scaled(label("？", 150, stroke_fill=(80, 130, 20)), s), cx + 330, cy - 280, alpha=a)


def scene_enzyme(frame, lt, sc):
    cx, cy = W / 2, 930
    p = ease_out_back(prog(lt, 0, 0.5), 1.5)
    paste_center(frame, soft_shadow(420, 70), cx, cy + 220)
    paste_center(frame, scaled(HALF, (0.5 + 0.5 * p) * 1.0), cx, cy)
    s, a = pop_scale(lt, 0.9)
    if a > 0:
        tag = label("アクチニジン", 76, fill=(255, 255, 255), stroke_fill=(80, 130, 20))
        paste_center(frame, scaled(tag, s), cx, cy + 300, alpha=a)
        sub = label("（たんぱく質を分解する酵素）", 40, fill=(80, 60, 30), stroke=0)
        paste_center(frame, sub, cx, cy + 368, alpha=a)
    if lt > 0.9:
        draw_sparkles(frame, lt, cx, cy, 320, 5, n=7)


GRATE = sprite(130, 90, lambda d, k, img: d.ellipse((0, 0, img.width - 1, img.height - 1), fill=(140, 196, 60, 230)))


def make_clock():
    def fn(d, k, img):
        ww = img.width
        d.ellipse((0, 0, ww - 1, ww - 1), fill=(255, 255, 255, 255), outline=(80, 130, 20, 255), width=int(10 * k))
        for i in range(12):
            a = i * math.pi / 6
            c = ww / 2
            d.line((c + math.cos(a) * ww * 0.36, c + math.sin(a) * ww * 0.36, c + math.cos(a) * ww * 0.42,
                    c + math.sin(a) * ww * 0.42), fill=(120, 120, 120, 255), width=int(5 * k))
    return sprite(220, 220, fn)


CLOCK = make_clock()


def scene_marinate(frame, lt, sc):
    cx, cy = W / 2, 1050
    soft = prog(lt, 1.2, 1.6)
    paste_center(frame, soft_shadow(520, 80), cx, cy + 140)
    paste_center(frame, STEAK, cx, cy)
    paste_center(frame, STEAK_SOFT, cx, cy, alpha=soft)
    rng = random.Random(4)
    for i in range(9):
        p = ease_out_cubic(prog(lt, 0.2 + i * 0.08, 0.35))
        if p > 0:
            x = cx + rng.uniform(-180, 180)
            y = cy + rng.uniform(-90, 60)
            paste_center(frame, scaled(GRATE, rng.uniform(0.7, 1.1)), x, y - 300 * (1 - p), alpha=p * (1 - soft * 0.6))
    # 時計
    ccx, ccy = cx + 300, cy - 330
    paste_center(frame, CLOCK, ccx, ccy)
    d = ImageDraw.Draw(frame)
    a = -math.pi / 2 + clamp((lt - 0.6) / 2.2) * 2 * math.pi
    d.line((ccx, ccy, ccx + math.cos(a) * 80, ccy + math.sin(a) * 80), fill=(214, 60, 40), width=8)
    d.ellipse((ccx - 10, ccy - 10, ccx + 10, ccy + 10), fill=(214, 60, 40))
    paste_center(frame, label("30分", 56, stroke_fill=(80, 130, 20)), ccx, ccy + 150)
    s, a2 = pop_scale(lt, 2.9)
    if a2 > 0:
        paste_center(frame, scaled(label("やわらか〜", 80, fill=(255, 250, 200), stroke_fill=(200, 90, 60)), s),
                     cx - 160, cy - 300, alpha=a2)
        draw_sparkles(frame, lt, cx, cy, 330, 3, n=6)


def make_cup(liquid=True):
    def fn(d, k, img):
        ww, hh = img.size
        d.polygon([(ww * 0.06, hh * 0.1), (ww * 0.94, hh * 0.1), (ww * 0.8, hh - 1), (ww * 0.2, hh - 1)],
                  fill=(230, 244, 255, 160), outline=(180, 200, 220, 255))
        top = hh * (0.3 if liquid else 0.22)
        pts = [(ww * (0.08 + 0.84 * i / 20), top + (math.sin(i * 1.3) * 8 * k if liquid else 0)) for i in range(21)]
        d.polygon(pts + [(ww * 0.8, hh - 4 * k), (ww * 0.2, hh - 4 * k)], fill=(150, 210, 80, 200))
        for i in range(5):
            x = ww * (0.3 + i * 0.1)
            d.ellipse((x - 14 * k, hh * 0.55 - 8 * k, x + 14 * k, hh * 0.55 + 8 * k), fill=(110, 170, 40, 255))
    return sprite(340, 380, fn)


CUP = make_cup()


def scene_jelly(frame, lt, sc):
    cx, cy = W / 2, 980
    wob = math.sin(lt * 8) * 0.04
    paste_center(frame, soft_shadow(300, 50), cx, cy + 200)
    paste_center(frame, scaled(CUP, 1.05 + wob, 1.05 - wob), cx, cy)
    s, a = pop_scale(lt, 0.8)
    if a > 0:
        paste_center(frame, scaled(label("ゼリーが\n固まらない…", 64, stroke_fill=(70, 110, 180)), s), cx + 260,
                     cy - 300, alpha=a)
    s, a = pop_scale(lt, 2.0)
    if a > 0:
        paste_center(frame, scaled(label("加熱すればOK", 60, fill=(255, 250, 200), stroke_fill=(80, 130, 20)), s),
                     cx, cy + 270, alpha=a)


def outro_subject(frame, cx, cy, s, lt):
    paste_center(frame, SHADOW, cx, cy + 250, alpha=0.8)
    paste_center(frame, scaled(KIWI, s * 0.9), cx - 160, cy + 40)
    paste_center(frame, scaled(HALF, s * 0.75), cx + 150, cy)


SCENES = [
    Scene(scene_hook, 3.0, "キウイで\nお肉がやわらか？", line="キウイで、お肉がやわらかくなるって、知ってた？",
          sub="キウイで、お肉がやわらかく\nなるって、知ってた？", sfx=[(0.2, "pop", {}), (1.3, "pop", {})]),
    Scene(scene_enzyme, 4.0, "ひみつは\n酵素！",
          line="キウイには、アクチニジンという、たんぱく質を分解する酵素があるんだワン！",
          sub="キウイには、アクチニジン\nという、たんぱく質を分解\nする酵素があるんだワン！",
          sfx=[(0.0, "chop", {}), (0.9, "ding", {})], jumps=[0.9]),
    Scene(scene_marinate, 4.2, "すりおろして\n漬けるだけ", line="すりおろして、お肉を三十分くらい漬けるだけで、やわらかくなるよ！",
          sub="すりおろして、お肉を30分\nくらい漬けるだけで、\nやわらかくなるよ！",
          sfx=[(0.2 + i * 0.08, "pop", {"f0": 400, "f1": 700, "amp": 0.12}) for i in range(9)]
          + [(2.9, "ding", {})], jumps=[2.9]),
    Scene(scene_jelly, 4.0, "注意！\nゼリーには…",
          line="だから、生のキウイを入れたゼラチンのゼリーは、固まりにくいんだよ！",
          sub="だから、生のキウイを入れた\nゼラチンのゼリーは、\n固まりにくいんだよ！",
          sfx=[(0.8, "boing", {"amp": 0.22}), (2.0, "pop", {})]),
    Scene(outro_draw(outro_subject), 3.0, OUTRO_TELOP, line=OUTRO_LINE, sub=OUTRO_SUB, happy=True,
          jumps=[0.1], sfx=[(0.1, "ding", {"amp": 0.35}), (1.0, "pop", {"f0": 500, "f1": 1300})], tail=0.9),
]

VIDEO = Video(8, SCENES, "kiwi.mp4",
              bg={"top": (248, 252, 236), "bottom": (214, 236, 170), "dot": (110, 160, 40, 28)},
              badge_color=(100, 150, 30), telop_stroke=(80, 130, 20), bubble_color=(110, 160, 40), bgm="fresh",
              bpm=116)

THUMB = ("キウイで\nお肉がやわらか！？", (160, 210, 80))


def thumb_subject(f):
    paste_center(f, soft_shadow(520, 80), W / 2 + 120, 1290)
    paste_center(f, STEAK, W / 2 + 140, 1170)
    paste_center(f, scaled(HALF, 0.95), W / 2 - 170, 980)
    paste_center(f, label("やわらか〜", 76, fill=(255, 250, 200), stroke_fill=(200, 90, 60)), 800, 960)


if __name__ == "__main__":
    VIDEO.render()
