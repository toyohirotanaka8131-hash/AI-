#!/usr/bin/env python3
"""#6 りんご「蜜入りりんごの蜜って甘い？」"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

from engine import (OUTRO_LINE, OUTRO_SUB, OUTRO_TELOP, W, Scene, Video, ball, clamp, draw_sparkles,
                    ease_out_back, ease_out_cubic, label, outro_draw, paste_center, pop_scale, prog, rotated,
                    scaled, soft_shadow, sprite)

RED = ((255, 120, 110), (214, 30, 40), (130, 10, 24))


def make_apple(size):
    body = ball(size, *RED, squash=0.9, light=(-0.35, -0.35), spec=0.6)
    out = Image.new("RGBA", (size, int(size * 1.15)), (0, 0, 0, 0))
    out.alpha_composite(body, (0, int(size * 0.15)))
    d = ImageDraw.Draw(out)
    c = size / 2
    top = size * 0.15 + size * 0.5 * (1 - 0.9) + 6
    d.ellipse((c - size * 0.12, top - 4, c + size * 0.12, top + size * 0.07), fill=(150, 20, 30, 200))
    d.line((c, top + 12, c + 8, top - size * 0.13), fill=(110, 70, 30), width=max(4, size // 40))
    leaf = sprite(size * 0.32, size * 0.15, lambda dd, k, img: dd.ellipse((0, 0, img.width - 1, img.height - 1),
                                                                           fill=(80, 160, 60, 255)))
    out.alpha_composite(rotated(leaf, 25), (int(c + 8), int(top - size * 0.2)))
    return out


def make_section(size):
    """横に切った断面：星形の芯と、そのまわりの蜜。"""
    def fn(d, k, img):
        S = size * k
        c = S / 2
        d.ellipse((0, 0, S - 1, S - 1), fill=(200, 26, 36, 255))
        d.ellipse((10 * k, 10 * k, S - 10 * k, S - 10 * k), fill=(255, 246, 214, 255))
    img = sprite(size, size, fn)
    c = size / 2
    honey = Image.new("RGBA", img.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(honey)
    rng = random.Random(6)
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        for j in range(6):
            r = size * rng.uniform(0.16, 0.34)
            aa = a + rng.uniform(-0.35, 0.35)
            x, y = c + math.cos(aa) * r, c + math.sin(aa) * r
            rr = size * rng.uniform(0.05, 0.09)
            hd.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(240, 206, 110, 120))
    img.alpha_composite(honey.filter(ImageFilter.GaussianBlur(size * 0.008)))
    gl = ImageDraw.Draw(img)
    for i in range(14):
        a = rng.uniform(0, 2 * math.pi)
        r = size * rng.uniform(0.17, 0.33)
        x, y = c + math.cos(a) * r, c + math.sin(a) * r
        gl.ellipse((x - 5, y - 3, x + 5, y + 3), fill=(255, 255, 250, 200))
    d = ImageDraw.Draw(img)
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = size * (0.15 if i % 2 == 0 else 0.07)
        pts.append((c + math.cos(a) * r, c + math.sin(a) * r))
    d.polygon(pts, fill=(246, 224, 170), outline=(190, 150, 80))
    d.line(pts + [pts[0]], fill=(190, 150, 80), width=max(3, size // 120))
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        x, y = c + math.cos(a) * size * 0.1, c + math.sin(a) * size * 0.1
        s = size * 0.025
        d.ellipse((x - s, y - s * 1.6, x + s, y + s * 1.6), fill=(110, 60, 30))
    return img


APPLE = make_apple(440)
SECTION = make_section(620)
SHADOW = soft_shadow(400, 70)
CUT = 0.7


def scene_hook(frame, lt, sc):
    cx, cy = W / 2, 1010
    rot = math.sin(lt * 2.2) * 6
    paste_center(frame, SHADOW, cx, cy + 260)
    s = ease_out_back(prog(lt, 0, 0.5), 1.6)
    paste_center(frame, rotated(scaled(APPLE, 0.5 + 0.5 * s), rot), cx, cy)
    s2, a = pop_scale(lt, 1.3)
    if a > 0:
        paste_center(frame, scaled(label("？", 160, stroke_fill=(190, 20, 40)), s2), cx + 300, cy - 260, alpha=a)


def make_knife():
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((ww * 0.3, 0, ww * 0.7, hh * 0.3), radius=int(16 * k), fill=(120, 72, 40, 255))
        d.polygon([(ww * 0.25, hh * 0.3), (ww * 0.75, hh * 0.3), (ww * 0.75, hh * 0.92), (ww * 0.5, hh)],
                  fill=(214, 220, 228, 255), outline=(150, 160, 170, 255))
    return sprite(90, 620, fn)


KNIFE = make_knife()


def scene_cut(frame, lt, sc):
    cx, cy = W / 2, 1010
    if lt < CUT + 0.1:
        paste_center(frame, SHADOW, cx, cy + 260)
        paste_center(frame, APPLE, cx, cy)
        p = clamp(lt / CUT) ** 2
        paste_center(frame, rotated(KNIFE, 90), cx + 700 - 700 * p, cy + 20)
    else:
        p = ease_out_back(prog(lt, CUT + 0.1, 0.5), 1.4)
        paste_center(frame, soft_shadow(560, 80), cx, cy + 330)
        paste_center(frame, scaled(SECTION, 0.4 + 0.6 * p), cx, cy)
        if lt > 1.4:
            draw_sparkles(frame, lt, cx, cy, 260, 6, n=7)
        s, a = pop_scale(lt, 1.5)
        if a > 0:
            d = ImageDraw.Draw(frame)
            d.line((cx + 270, cy - 330, cx + 110, cy - 110), fill=(200, 140, 0, int(255 * a)), width=8)
            paste_center(frame, scaled(label("蜜", 110, fill=(255, 236, 140), stroke_fill=(190, 110, 0)), s),
                         cx + 300, cy - 390, alpha=a)


def make_meter(frac, color):
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((0, 0, ww - 1, hh - 1), radius=int(26 * k), fill=(255, 255, 255, 255),
                            outline=(210, 200, 190, 255), width=int(4 * k))
        if frac > 0:
            d.rounded_rectangle((8 * k, 8 * k, 8 * k + (ww - 16 * k) * frac, hh - 8 * k), radius=int(20 * k),
                                fill=color + (255,))
    return sprite(620, 70, fn)


METERS = {}


def meter(frac, color):
    key = (round(frac, 2), color)
    if key not in METERS:
        METERS[key] = make_meter(frac, color)
    return METERS[key]


def scene_truth(frame, lt, sc):
    cx, cy = W / 2, 860
    paste_center(frame, scaled(SECTION, 0.52), cx, cy - 60)
    s, a = pop_scale(lt, 0.3)
    if a > 0:
        paste_center(frame, scaled(label("正体はソルビトール", 62, stroke_fill=(190, 110, 0)), s), cx, cy + 210,
                     alpha=a)
    y0 = cy + 330
    for i, (name, frac, col) in enumerate((("砂糖", 1.0, (240, 120, 60)), ("蜜", 0.6, (236, 190, 80)))):
        p = ease_out_cubic(prog(lt, 0.9 + i * 0.7, 0.8))
        if p <= 0:
            continue
        y = y0 + i * 110
        paste_center(frame, label(name, 56, fill=(110, 60, 20), stroke=0), cx - 380, y)
        paste_center(frame, meter(frac * p, col), cx + 70, y)
    s, a = pop_scale(lt, 2.4)
    if a > 0:
        paste_center(frame, scaled(label("甘さひかえめ", 58, fill=(255, 250, 200), stroke_fill=(190, 110, 0)), s),
                     cx + 230, y0 + 185, alpha=a)


def make_ribbon(text, color):
    t = label(text, 70, stroke=0)
    img = sprite(t.width + 120, t.height + 40,
                 lambda d, k, im: d.polygon([(0, 0), (im.width - 1, 0), (im.width - 30 * k, im.height / 2),
                                             (im.width - 1, im.height - 1), (0, im.height - 1),
                                             (30 * k, im.height / 2)], fill=color + (255,)))
    img.alpha_composite(t, (60, 20))
    return img


RIBBON = make_ribbon("完熟のサイン", (214, 30, 40))


def scene_reason(frame, lt, sc):
    cx, cy = W / 2, 950
    p = ease_out_back(prog(lt, 0, 0.5), 1.5)
    paste_center(frame, SHADOW, cx, cy + 280)
    paste_center(frame, scaled(APPLE, (0.6 + 0.4 * p) * 1.05), cx, cy)
    s, a = pop_scale(lt, 0.8)
    if a > 0:
        paste_center(frame, scaled(RIBBON, s), cx, cy + 300, alpha=a)
    if lt > 0.8:
        draw_sparkles(frame, lt, cx, cy, 330, 7, n=8)


def outro_subject(frame, cx, cy, s, lt):
    paste_center(frame, SHADOW, cx - 120, cy + 270, alpha=0.8)
    paste_center(frame, scaled(APPLE, s * 0.9), cx - 120, cy)
    paste_center(frame, scaled(SECTION, s * 0.45), cx + 190, cy + 120)


SCENES = [
    Scene(scene_hook, 3.0, "蜜入りりんごの\n蜜って甘い？", line="りんごの蜜って、甘いと思う？",
          sub="りんごの蜜って、\n甘いと思う？", sfx=[(1.3, "pop", {})]),
    Scene(scene_cut, 3.6, "これが\n「蜜」", line="切ったときの、この透き通ったところが蜜！",
          sub="切ったときの、この\n透き通ったところが蜜！", sfx=[(CUT, "chop", {}), (1.5, "ding", {})]),
    Scene(scene_truth, 4.0, "蜜そのものは\nそれほど甘くない！", line="実は、蜜そのものは、それほど甘くないんだワン！",
          sub="実は、蜜そのものは、\nそれほど甘くないんだワン！",
          sfx=[(0.3, "pop", {}), (0.9, "shake", {"dur": 0.8}), (1.6, "shake", {"dur": 0.8}),
               (2.4, "boing", {"amp": 0.2})], jumps=[2.4]),
    Scene(scene_reason, 4.0, "蜜入り＝\nよく熟したサイン", line="でも、蜜があるのは、よく熟したサイン。だから、甘くておいしいんだよ！",
          sub="でも、蜜があるのは\nよく熟したサイン。だから、\n甘くておいしいんだよ！", sfx=[(0.8, "ding", {})]),
    Scene(outro_draw(outro_subject), 3.0, OUTRO_TELOP, line=OUTRO_LINE, sub=OUTRO_SUB, happy=True,
          jumps=[0.1], sfx=[(0.1, "ding", {"amp": 0.35}), (1.0, "pop", {"f0": 500, "f1": 1300})], tail=0.9),
]

VIDEO = Video(6, SCENES, "ringo.mp4",
              bg={"top": (255, 248, 240), "bottom": (255, 214, 200), "dot": (214, 40, 50, 24)},
              badge_color=(200, 40, 50), telop_stroke=(180, 20, 40), bubble_color=(210, 60, 70), bgm="sweet",
              bpm=114)

THUMB = ("蜜入りりんごの\n蜜って甘い？", (255, 140, 120))


def thumb_subject(f):
    paste_center(f, soft_shadow(480, 80), W / 2 - 150, 1330)
    paste_center(f, scaled(APPLE, 1.05), W / 2 - 150, 1050)
    paste_center(f, scaled(SECTION, 0.62), W / 2 + 230, 1150)
    paste_center(f, label("？", 160, stroke_fill=(180, 20, 40), stroke=14), 960, 900)


if __name__ == "__main__":
    VIDEO.render()
