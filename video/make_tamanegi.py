#!/usr/bin/env python3
"""#9 たまねぎ「切ると涙が出るのはなぜ？」"""
import math
import random

from PIL import Image, ImageDraw

import engine as E
from engine import (OUTRO_LINE, OUTRO_SUB, OUTRO_TELOP, W, Scene, Video, ball, clamp, draw_sparkles,
                    ease_out_back, ease_out_cubic, label, outro_draw, paste_center, pop_scale, prog, rotated,
                    scaled, soft_shadow, sprite)

SKIN_L, SKIN, SKIN_D = (240, 196, 120), (206, 140, 60), (150, 90, 30)


def make_onion(size):
    out = Image.new("RGBA", (size, int(size * 1.3)), (0, 0, 0, 0))
    body = ball(size, SKIN_L, SKIN, SKIN_D, squash=0.92, light=(-0.3, -0.25), spec=0.3)
    oy = int(size * 0.3)
    out.alpha_composite(body, (0, oy))

    def top_fn(d, k, img):
        ww, hh = img.size
        d.polygon([(ww * 0.5, 0), (ww * 0.92, hh), (ww * 0.08, hh)], fill=SKIN + (255,))
        d.line((ww * 0.5, 0, ww * 0.55, hh * 0.5), fill=SKIN_D + (255,), width=int(4 * k))
    top = sprite(size * 0.5, size * 0.42, top_fn)
    out.alpha_composite(top, (int(size * 0.25), oy - int(size * 0.32)))
    d = ImageDraw.Draw(out)
    c = size / 2
    for i in range(-3, 4):
        pts = []
        for j in range(21):
            t = j / 20
            ang = math.pi * (0.1 + 0.8 * t)
            x = c + i * size * 0.12 * math.sin(ang)
            y = oy - size * 0.05 + size * 0.95 * t
            pts.append((x, y))
        d.line(pts, fill=SKIN_D + (110,), width=max(2, size // 120))
    for i in range(7):
        x = c + (i - 3) * size * 0.04
        d.line((x, oy + size * 0.9, x + (i - 3) * 6, oy + size * 1.0), fill=(230, 220, 190), width=max(2, size // 90))
    return out


ONION = make_onion(420)
SHADOW = soft_shadow(380, 60)


def make_knife():
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((ww * 0.3, 0, ww * 0.7, hh * 0.3), radius=int(16 * k), fill=(40, 40, 46, 255))
        d.polygon([(ww * 0.25, hh * 0.3), (ww * 0.75, hh * 0.3), (ww * 0.75, hh * 0.92), (ww * 0.5, hh)],
                  fill=(214, 220, 228, 255), outline=(150, 160, 170, 255))
        d.line((ww * 0.3, hh * 0.32, ww * 0.3, hh * 0.9), fill=(255, 255, 255, 255), width=int(6 * k))
    return sprite(110, 700, fn)


KNIFE = make_knife()
TEAR = sprite(30, 44, lambda d, k, img: (d.polygon([(img.width / 2, 0), (img.width - 2 * k, img.height * 0.62),
                                                    (2 * k, img.height * 0.62)], fill=(120, 190, 255, 240)),
                                         d.ellipse((2 * k, img.height * 0.3, img.width - 2 * k, img.height - 1),
                                                   fill=(120, 190, 255, 240))))


def draw_tears(frame, lt, strength=1.0):
    """コロの目から涙。"""
    sx, sy = E.DOG_X - E.DOG_W * E.DOG_SCALE / 2, E.DOG_Y - E.DOG_H * E.DOG_SCALE / 2
    for i, ex in enumerate((118, 202)):
        x = sx + ex * E.DOG_SCALE + (-22 if i == 0 else 22)
        y0 = sy + 165 * E.DOG_SCALE
        for j in range(2):
            q = ((lt / 0.7) + j * 0.5 + i * 0.25) % 1.0
            paste_center(frame, TEAR, x + (-1 if i == 0 else 1) * q * 18, y0 + q * 90, alpha=strength * (1 - q))


def scene_hook(frame, lt, sc):
    cx, cy = W / 2 - 80, 1010
    paste_center(frame, SHADOW, cx, cy + 300)
    paste_center(frame, ONION, cx, cy)
    for c in (0.6, 1.1, 1.6):
        if c - 0.3 <= lt < c + 0.2:
            p = clamp((lt - (c - 0.3)) / 0.3)
            paste_center(frame, KNIFE, cx + 290, cy - 80 + 120 * ease_out_cubic(p))
            break
    else:
        paste_center(frame, KNIFE, cx + 290, cy - 80)
    s, a = pop_scale(lt, 1.8)
    if a > 0:
        paste_center(frame, scaled(label("なぜ？", 100, stroke_fill=(150, 90, 30)), s), cx - 230, cy - 320, alpha=a)


# ---- 細胞がこわれる
def make_cells(size, broken):
    def fn(d, k, img):
        S = size * k
        c = S / 2
        d.ellipse((0, 0, S - 1, S - 1), fill=(252, 248, 230, 255))
        r = 46 * k
        rng = random.Random(3)
        for row in range(-6, 7):
            for col in range(-6, 7):
                x = c + col * r * 1.75 + (r * 0.87 if row % 2 else 0)
                y = c + row * r * 1.5
                if (x - c) ** 2 + (y - c) ** 2 > (S / 2 - r) ** 2:
                    continue
                pts = [(x + math.cos(a) * r * 0.95, y + math.sin(a) * r * 0.95)
                       for a in [math.pi / 6 + i * math.pi / 3 for i in range(6)]]
                if broken and rng.random() < 0.6:
                    d.polygon(pts, fill=(250, 236, 220, 255), outline=(200, 170, 130, 255))
                    d.line((x - r * 0.5, y - r * 0.4, x, y + r * 0.1, x + r * 0.4, y - r * 0.3),
                           fill=(170, 120, 80, 255), width=int(4 * k))
                else:
                    d.polygon(pts, fill=(238, 244, 210, 255), outline=(190, 200, 150, 255))
                    d.ellipse((x - r * 0.2, y - r * 0.2, x + r * 0.2, y + r * 0.2), fill=(200, 214, 160, 255))
        d.ellipse((0, 0, S - 1, S - 1), outline=(120, 90, 60, 255), width=int(16 * k))
    return sprite(size, size, fn)


CELLS = make_cells(660, False)
CELLS_BROKEN = make_cells(660, True)
GAS = sprite(46, 46, lambda d, k, img: d.ellipse((0, 0, img.width - 1, img.height - 1), fill=(190, 140, 230, 200)))
BREAK = 1.0


def scene_cells(frame, lt, sc):
    cx, cy = W / 2, 940
    paste_center(frame, scaled(CELLS, 0.85), cx, cy)
    b = prog(lt, BREAK, 0.4)
    paste_center(frame, scaled(CELLS_BROKEN, 0.85), cx, cy, alpha=b)
    if lt > BREAK:
        rng = random.Random(7)
        for i in range(22):
            ph = rng.uniform(0, 1)
            q = ((lt - BREAK) / 1.6 + ph) % 1.0
            x = cx + rng.uniform(-260, 260) + math.sin(q * 8 + i) * 30
            y = cy + rng.uniform(-100, 200) - q * 500
            paste_center(frame, scaled(GAS, 0.6 + q), x, y, alpha=0.85 * math.sin(q * math.pi) * b)
    s, a = pop_scale(lt, 1.6)
    if a > 0:
        paste_center(frame, scaled(label("目にしみる成分", 66, fill=(255, 255, 255), stroke_fill=(140, 80, 190)), s),
                     cx, cy + 340, alpha=a)


# ---- 冷やす
def make_fridge():
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((0, 0, ww - 1, hh - 1), radius=int(40 * k), fill=(236, 246, 255, 255),
                            outline=(150, 190, 230, 255), width=int(10 * k))
        d.line((10 * k, hh * 0.36, ww - 10 * k, hh * 0.36), fill=(150, 190, 230, 255), width=int(8 * k))
        for y0, y1 in ((hh * 0.1, hh * 0.28), (hh * 0.46, hh * 0.7)):
            d.rounded_rectangle((ww - 50 * k, y0, ww - 30 * k, y1), radius=int(8 * k), fill=(150, 190, 230, 255))
    return sprite(460, 760, fn)


FRIDGE = make_fridge()
SNOW = sprite(60, 60, lambda d, k, img: [d.line((img.width / 2 + math.cos(a) * 28 * k,
                                                 img.height / 2 + math.sin(a) * 28 * k,
                                                 img.width / 2 - math.cos(a) * 28 * k,
                                                 img.height / 2 - math.sin(a) * 28 * k),
                                                fill=(150, 200, 255, 255), width=int(6 * k))
                                         for a in (0, math.pi / 3, 2 * math.pi / 3)])


def scene_fridge(frame, lt, sc):
    cx, cy = W / 2 + 60, 1000
    p = ease_out_back(prog(lt, 0, 0.5), 1.4)
    paste_center(frame, soft_shadow(420, 60), cx, cy + 390)
    paste_center(frame, scaled(FRIDGE, 0.6 + 0.4 * p), cx, cy)
    paste_center(frame, scaled(ONION, 0.5), cx - 20, cy + 120)
    rng = random.Random(2)
    for i in range(8):
        ph = rng.uniform(0, 1)
        q = ((lt / 2.0) + ph) % 1.0
        paste_center(frame, rotated(SNOW, q * 180), cx + rng.uniform(-300, 300), cy - 420 + q * 700,
                     alpha=math.sin(q * math.pi))
    s, a = pop_scale(lt, 1.2)
    if a > 0:
        paste_center(frame, scaled(label("ひんやり", 76, stroke_fill=(60, 140, 220)), s), cx - 330, cy - 250, alpha=a)


# ---- よく切れる包丁
def make_half_onion(size):
    def fn(d, k, img):
        S = size * k
        c = S / 2
        for i in range(8, 0, -1):
            r = S * 0.5 * i / 8
            col = (250, 246, 226, 255) if i % 2 else (236, 230, 200, 255)
            d.ellipse((c - r, c - r * 0.9, c + r, c + r * 0.9), fill=col, outline=(210, 200, 160, 255),
                      width=int(3 * k))
        d.ellipse((0, 0, S - 1, S * 0.9), outline=SKIN + (255,), width=int(10 * k))
    return sprite(size, size, fn)


HALF = make_half_onion(480)


def scene_knife(frame, lt, sc):
    cx, cy = W / 2 - 60, 1040
    paste_center(frame, soft_shadow(420, 60), cx, cy + 230)
    paste_center(frame, HALF, cx, cy)
    p = prog(lt, 0.3, 0.5)
    y = cy - 460 + 340 * ease_out_cubic(p)
    paste_center(frame, rotated(KNIFE, -8), cx + 300, y)
    if lt > 0.85:
        draw_sparkles(frame, lt, cx + 300, y + 100, 120, 3, n=4)
    s, a = pop_scale(lt, 1.0)
    if a > 0:
        paste_center(frame, scaled(label("スパッ！", 90, stroke_fill=(60, 140, 220)), s), cx - 160, cy - 330, alpha=a)


def outro_subject(frame, cx, cy, s, lt):
    paste_center(frame, SHADOW, cx, cy + 300, alpha=0.8)
    paste_center(frame, scaled(ONION, s), cx, cy)


def crying(draw):
    def wrapped(frame, lt, sc):
        draw(frame, lt, sc)
    return wrapped


SCENES = [
    Scene(scene_hook, 3.0, "たまねぎで\n涙が出るのはなぜ？", line="たまねぎを切ると、涙が出るのはなぜ？",
          sub="たまねぎを切ると、\n涙が出るのはなぜ？", sfx=[(0.6, "chop", {}), (1.1, "chop", {}), (1.6, "chop", {}),
                                                (1.8, "pop", {})]),
    Scene(scene_cells, 4.4, "細胞がこわれて\n成分が飛び出す！",
          line="切ると細胞がこわれて、目にしみる成分が、空気中に飛び出すんだワン！",
          sub="切ると細胞がこわれて、\n目にしみる成分が、空気中に\n飛び出すんだワン！",
          sfx=[(BREAK, "chop", {}), (1.6, "boing", {"amp": 0.2})]),
    Scene(scene_fridge, 4.0, "コツ①\n冷やしてから切る", line="冷蔵庫で冷やしてから切ると、成分が飛びにくくなるよ！",
          sub="冷蔵庫で冷やしてから切ると、\n成分が飛びにくくなるよ！", sfx=[(1.2, "ding", {})], jumps=[1.2]),
    Scene(scene_knife, 4.0, "コツ②\nよく切れる包丁で", line="よく切れる包丁なら、細胞がつぶれにくくて、涙が出にくいんだ！",
          sub="よく切れる包丁なら、細胞が\nつぶれにくくて、\n涙が出にくいんだ！",
          sfx=[(0.75, "chop", {}), (1.0, "ding", {})], jumps=[1.0]),
    Scene(outro_draw(outro_subject), 3.0, OUTRO_TELOP, line=OUTRO_LINE, sub=OUTRO_SUB, happy=True,
          jumps=[0.1], sfx=[(0.1, "ding", {"amp": 0.35}), (1.0, "pop", {"f0": 500, "f1": 1300})], tail=0.9),
]


class OnionVideo(Video):
    def render_frame(self, tr, mouth=0):
        img = super().render_frame(tr, mouth)
        sc = self.scene_at(tr)
        if sc in self.scenes[:2]:
            frame = img.convert("RGBA")
            draw_tears(frame, tr - sc.start, clamp((tr - 0.9) * 2))
            return frame.convert("RGB")
        return img


VIDEO = OnionVideo(9, SCENES, "tamanegi.mp4",
                   bg={"top": (252, 248, 240), "bottom": (240, 222, 196), "dot": (180, 130, 60, 26)},
                   badge_color=(170, 110, 40), telop_stroke=(150, 90, 30), bubble_color=(190, 130, 60), bgm="uke",
                   bpm=112)

THUMB = ("たまねぎで\n涙が出るのはなぜ？", (230, 180, 110))


def thumb_subject(f):
    paste_center(f, SHADOW, W / 2 + 60, 1340)
    paste_center(f, ONION, W / 2 + 60, 1040)
    paste_center(f, KNIFE, W / 2 + 380, 980)
    for i, (x, y) in enumerate(((330, 1420), (400, 1450))):
        paste_center(f, scaled(TEAR, 1.6), x, y)


if __name__ == "__main__":
    VIDEO.render()
