#!/usr/bin/env python3
"""#4 バナナ「茶色い点は捨てるサインじゃない」"""
import math
import random

from PIL import Image, ImageDraw

from engine import (OUTRO_LINE, OUTRO_SUB, OUTRO_TELOP, W, Scene, Video, clamp, draw_sparkles, ease_in_out,
                    ease_out_back, ease_out_cubic, label, outro_draw, paste_center, pop_scale, prog, rotated,
                    scaled, soft_shadow, sprite)

YELLOW = ((255, 236, 120), (250, 206, 40), (214, 160, 20))
GREEN = ((190, 220, 110), (130, 180, 60), (90, 130, 40))
BROWN = (110, 66, 30)


def banana_geom(w, h, k):
    """バナナの外形（三日月）の点列。"""
    R = w * k * 0.62
    cx, cy = w * k / 2, h * k * 0.18 + R
    A = 0.72
    T = h * k * 0.3
    top, bot, mid = [], [], []
    n = 60
    for i in range(n + 1):
        t = i / n
        th = -A + 2 * A * t
        dx, dy = math.sin(th), -math.cos(th)
        hh = T * (math.sin(math.pi * (0.04 + 0.92 * t)) ** 0.55)
        top.append((cx + dx * (R + hh * 0.55), cy + dy * (R + hh * 0.55)))
        bot.append((cx + dx * (R - hh), cy + dy * (R - hh)))
        mid.append((cx + dx * (R - hh * 0.2), cy + dy * (R - hh * 0.2), hh))
    return top, bot, mid, (cx, cy, R, A)


def make_banana(w, h, colors):
    light, base, dark = colors

    def fn(d, k, img):
        top, bot, mid, (cx, cy, R, A) = banana_geom(w, h, k)
        d.polygon(top + bot[::-1], fill=base + (255,))
        # 下側の影と上側のつや
        shade = [(x, y) for x, y in bot] + [(cx + (mx - cx) * 0.995, cy + (my - cy) * 0.995)
                                            for mx, my, _ in mid[::-1]]
        d.polygon(shade, fill=dark + (120,))
        d.line([(cx + (x - cx) * 0.985, cy + (y - cy) * 0.985) for x, y in top[6:-6]], fill=light + (255,),
               width=int(14 * k))
        # 稜線
        d.line([(mx, my) for mx, my, _ in mid[4:-4]], fill=dark + (110,), width=int(4 * k))
        # 軸と先端
        x0, y0 = top[0]
        d.polygon([(x0 + 6 * k, y0 + 10 * k), (x0 - 46 * k, y0 - 30 * k), (x0 - 30 * k, y0 - 50 * k),
                   (x0 + 22 * k, y0 + 2 * k)], fill=(120, 140, 60, 255))
        xe, ye = bot[-1]
        d.ellipse((xe - 14 * k, ye - 14 * k, xe + 14 * k, ye + 14 * k), fill=BROWN + (255,))
    return sprite(w, h, fn)


def make_spots(w, h, n, seed=1, big=1.0):
    rng = random.Random(seed)

    def fn(d, k, img):
        top, bot, mid, _ = banana_geom(w, h, k)
        for _ in range(n):
            i = rng.randint(8, len(mid) - 8)
            mx, my, hh = mid[i]
            ox = rng.uniform(-0.6, 0.45) * hh
            x, y = mx, my + ox
            r = rng.uniform(4, 11) * k * big
            d.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=BROWN + (rng.randint(170, 240),))
    return sprite(w, h, fn)


BAN_W, BAN_H = 620, 330
BAN_Y = make_banana(BAN_W, BAN_H, YELLOW)
BAN_G = make_banana(BAN_W, BAN_H, GREEN)
SPOTS = make_spots(BAN_W, BAN_H, 70, 1)
BIG_W, BIG_H = 900, 480
BIG_BAN = make_banana(BIG_W, BIG_H, YELLOW)
BIG_SPOTS = make_spots(BIG_W, BIG_H, 80, 2, big=1.4)
SHADOW = soft_shadow(500, 70)


def spotted(scale=1.0, spots=1.0, green=0.0):
    img = BAN_Y.copy()
    if green > 0:
        img.alpha_composite(BAN_G.copy() if green >= 1 else _alpha_img(BAN_G, green))
    if spots > 0:
        img.alpha_composite(SPOTS if spots >= 1 else _alpha_img(SPOTS, spots))
    return scaled(img, scale)


def _alpha_img(img, a):
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return out


# ---- ゴミ箱の前でストップ
def make_bin():
    def fn(d, k, img):
        ww, hh = img.size
        d.polygon([(ww * 0.08, hh * 0.22), (ww * 0.92, hh * 0.22), (ww * 0.82, hh), (ww * 0.18, hh)],
                  fill=(150, 160, 172, 255), outline=(110, 118, 128, 255))
        for i in range(4):
            x = ww * (0.3 + i * 0.13)
            d.line((x, hh * 0.32, x - (i - 1.5) * 6 * k, hh * 0.92), fill=(124, 132, 144, 255), width=int(8 * k))
        d.rounded_rectangle((0, hh * 0.12, ww - 1, hh * 0.24), radius=int(14 * k), fill=(124, 132, 144, 255))
        d.rounded_rectangle((ww * 0.38, 0, ww * 0.62, hh * 0.14), radius=int(10 * k), fill=(124, 132, 144, 255))
    return sprite(380, 460, fn)


BIN = make_bin()
STOP = 1.0


def scene_stop(frame, lt, sc):
    bx, by = W / 2 + 180, 1180
    paste_center(frame, BIN, bx, by)
    p = ease_out_cubic(clamp(lt / STOP))
    x = W / 2 - 300 + 330 * p
    y = 700 + 150 * p
    rot = -20 * p
    if lt > STOP:
        q = prog(lt, STOP, 0.6)
        rot += math.sin(q * 30) * 8 * (1 - q)
        y -= 60 * ease_out_back(prog(lt, STOP, 0.5))
    paste_center(frame, rotated(spotted(0.85), rot), x, y)
    s, a = pop_scale(lt, STOP + 0.05)
    if a > 0:
        paste_center(frame, scaled(label("！", 200, fill=(255, 240, 90), stroke_fill=(214, 120, 0), stroke=16), s),
                     x + 260, y - 170, alpha=a)
        stop = sprite(300, 120, lambda d, k, img: d.rounded_rectangle((0, 0, img.width - 1, img.height - 1),
                                                                     radius=int(30 * k), fill=(230, 60, 60, 255)))
        stop.alpha_composite(label("STOP", 70, stroke=0), (60, 18))
        paste_center(frame, scaled(stop, s), bx, by - 330, alpha=a)


# ---- シュガースポット
def scene_spots(frame, lt, sc):
    cx, cy = W / 2, 1000
    z = 0.9 + 0.1 * ease_out_cubic(prog(lt, 0, 0.6))
    paste_center(frame, SHADOW, cx, cy + 230)
    img = BIG_BAN.copy()
    img.alpha_composite(BIG_SPOTS)
    paste_center(frame, scaled(img, z), cx, cy)
    # 虫めがね
    k = prog(lt, 0.8, 0.5)
    if k > 0:
        mx, my = cx + 40 + math.sin(lt * 1.5) * 120, cy - 20
        lens = sprite(300, 380, lambda d, kk, im: (
            d.ellipse((10 * kk, 10 * kk, 290 * kk, 290 * kk), outline=(90, 70, 50, 255), width=int(18 * kk)),
            d.ellipse((28 * kk, 28 * kk, 272 * kk, 272 * kk), fill=(255, 255, 255, 50)),
            d.rounded_rectangle((130 * kk, 285 * kk, 170 * kk, 380 * kk), radius=int(14 * kk),
                                fill=(120, 72, 40, 255))))
        paste_center(frame, rotated(lens, -20), mx, my + 60, alpha=clamp(k * 2))
    s, a = pop_scale(lt, 1.3)
    if a > 0:
        paste_center(frame, scaled(label("あまい！", 80, fill=(255, 245, 170), stroke_fill=(170, 100, 0)), s),
                     cx + 260, cy - 300, alpha=a)


# ---- 熟していく
def make_gauge():
    def fn(d, k, img):
        ww, hh = img.size
        cols = [(130, 180, 60), (250, 206, 40), (190, 120, 40)]
        seg = ww / 3
        for i, c in enumerate(cols):
            d.rounded_rectangle((i * seg + 4 * k, 0, (i + 1) * seg - 4 * k, hh - 1), radius=int(22 * k),
                                fill=c + (255,))
    return sprite(840, 46, fn)


GAUGE = make_gauge()
RIPE = [(0.3, 1.4), (1.4, 2.8)]


def scene_ripen(frame, lt, sc):
    cx, cy = W / 2, 940
    g = 1 - prog(lt, *RIPE[0]) if True else 0
    sp = ease_in_out(prog(lt, RIPE[1][0], RIPE[1][1] - RIPE[1][0]))
    paste_center(frame, SHADOW, cx, cy + 210)
    paste_center(frame, spotted(1.2, sp, g), cx, cy)
    gy = cy + 330
    paste_center(frame, GAUGE, cx, gy)
    for i, t in enumerate(("まだ", "黄色", "食べごろ！")):
        col = (190, 60, 0) if i == 2 else (120, 80, 30)
        paste_center(frame, label(t, 44, fill=(255, 255, 255), stroke_fill=col, stroke=7), cx - 280 + i * 280,
                     gy + 62)
    pos = (1 - g) * 0.5 + sp * 0.5
    px = cx - 280 + pos * 560
    ImageDraw.Draw(frame).polygon([(px - 24, gy - 64), (px + 24, gy - 64), (px, gy - 26)], fill=(230, 60, 60))
    if sp > 0.95:
        draw_sparkles(frame, lt, cx, cy, 380, 5, n=6)


# ---- 白い筋
def make_peeled():
    def fn(d, k, img):
        ww, hh = img.size
        c = ww / 2
        # 果肉
        fruit = []
        for i in range(41):
            t = i / 40
            y = hh * (0.04 + 0.7 * t)
            wdt = ww * 0.17 * (math.sin(math.pi * (0.12 + 0.88 * t)) ** 0.4) if t < 0.95 else ww * 0.1
            fruit.append((c + wdt + math.sin(t * 2) * 10 * k, y))
        left = [(2 * c - x + 20 * k * math.sin(i / 40 * 2), y) for i, (x, y) in enumerate(fruit)]
        d.polygon(fruit + left[::-1], fill=(246, 226, 170, 255))
        d.line(fruit + left[::-1] + [fruit[0]], fill=(206, 170, 90, 255), width=int(6 * k), joint="curve")
        # 白い筋
        for j in range(5):
            off = (j - 2) * ww * 0.05
            pts = [(c + off * math.sin(math.pi * (0.1 + 0.85 * i / 30)) + math.sin(i * 0.7 + j) * 4 * k,
                    hh * (0.08 + 0.62 * i / 30)) for i in range(31)]
            d.line(pts, fill=(255, 255, 255, 255), width=int(8 * k))
            d.line(pts, fill=(226, 206, 150, 255), width=int(2 * k))
        # 皮（3枚が垂れる）
        for sgn, sx in ((-1, -1), (0, 0), (1, 1)):
            base_y = hh * 0.62
            pts = [(c + sx * ww * 0.12 - ww * 0.11, base_y), (c + sx * ww * 0.12 + ww * 0.11, base_y),
                   (c + sx * ww * 0.36 + ww * 0.07, hh * 0.97), (c + sx * ww * 0.36 - ww * 0.07, hh * 0.99)]
            d.polygon(pts, fill=(250, 206, 40, 255) if sgn else (236, 190, 30, 255), outline=(214, 160, 20, 255))
        d.rounded_rectangle((c - ww * 0.14, hh * 0.88, c + ww * 0.14, hh), radius=int(16 * k),
                            fill=(214, 160, 20, 255))
        d.rectangle((c - ww * 0.04, hh * 0.95, c + ww * 0.04, hh), fill=(120, 140, 60, 255))
    return sprite(620, 860, fn)


PEELED = make_peeled()


def scene_strings(frame, lt, sc):
    cx, cy = W / 2 - 80, 960
    p = ease_out_back(prog(lt, 0, 0.5), 1.4)
    paste_center(frame, SHADOW, cx, cy + 370)
    paste_center(frame, scaled(PEELED, (0.6 + 0.4 * p) * 0.88), cx, cy)
    k = prog(lt, 0.9, 0.35)
    if k > 0:
        d = ImageDraw.Draw(frame)
        d.line((830, 760, cx + 20, cy - 160), fill=(110, 170, 80, int(255 * k)), width=8)
        d.ellipse((cx + 8, cy - 172, cx + 32, cy - 148), fill=(110, 170, 80, int(255 * k)))
        s, a = pop_scale(lt, 0.9)
        paste_center(frame, scaled(label("白い筋＝\n栄養の通り道", 54, stroke_fill=(70, 140, 50)), s), 850, 690,
                     alpha=a)
    s, a = pop_scale(lt, 2.2)
    if a > 0:
        paste_center(frame, scaled(label("食べてOK！", 76, fill=(255, 250, 200), stroke_fill=(214, 120, 0)), s),
                     cx + 320, cy + 260, alpha=a)


# ---- 締め：ヨーグルトにのせる
def make_bowl():
    def fn(d, k, img):
        ww, hh = img.size
        d.ellipse((0, 0, ww - 1, hh * 0.42), fill=(255, 255, 250, 255), outline=(220, 216, 206, 255),
                  width=int(5 * k))
        d.chord((0, -hh * 0.55, ww - 1, hh - 1), 0, 180, fill=(120, 170, 220, 255))
        d.ellipse((ww * 0.04, hh * 0.02, ww * 0.96, hh * 0.4), fill=(255, 254, 246, 255))
    return sprite(560, 420, fn)


BOWL = make_bowl()
SLICE = sprite(110, 110, lambda d, k, img: (
    d.ellipse((2 * k, 2 * k, img.width - 2 * k, img.height - 2 * k), fill=(255, 242, 200, 255),
              outline=(236, 214, 150, 255), width=int(5 * k)),
    [d.ellipse((img.width / 2 + math.cos(a) * 18 * k - 4 * k, img.height / 2 + math.sin(a) * 18 * k - 4 * k,
                img.width / 2 + math.cos(a) * 18 * k + 4 * k, img.height / 2 + math.sin(a) * 18 * k + 4 * k),
               fill=(180, 150, 100, 255)) for a in (0, 2.1, 4.2)]))


def outro_subject(frame, cx, cy, s, lt):
    paste_center(frame, SHADOW, cx, cy + 210, alpha=0.8)
    paste_center(frame, scaled(BOWL, s), cx, cy + 60)
    for i, (dx, dy) in enumerate(((-120, -60), (0, -80), (120, -60), (-60, -20), (60, -20))):
        p = ease_out_cubic(prog(lt, 0.15 + i * 0.12, 0.35))
        if p > 0:
            paste_center(frame, scaled(SLICE, s), cx + dx * s, cy + (dy - 400 * (1 - p)) * s + 30, alpha=p)


SCENES = [
    Scene(scene_stop, 3.2, "ちょっと\n待って！", line="その茶色い点のバナナ、捨てないで！",
          sub="その茶色い点のバナナ、\n捨てないで！", sfx=[(0.05, "whoosh", {"dur": 0.9}), (STOP, "boing", {}),
                                                (STOP + 0.05, "pop", {"f0": 300, "f1": 1400, "amp": 0.4})],
          jumps=[STOP]),
    Scene(scene_spots, 4.2, "名前は\nシュガースポット", line="この点は、シュガースポット。熟して甘くなったサインなんだワン！",
          sub="この点は、シュガースポット。\n熟して甘くなった\nサインなんだワン！", sfx=[(1.3, "ding", {})]),
    Scene(scene_ripen, 4.4, "点が出たら\n食べごろ！", line="点が出てきたころが、甘さのピークと言われているよ！",
          sub="点が出てきたころが、甘さの\nピークと言われているよ！",
          sfx=[(0.3, "shake", {"dur": 2.5}), (2.85, "ding", {})], jumps=[2.85]),
    Scene(scene_strings, 4.6, "白い筋は\n栄養の通り道", line="白い筋は、栄養や水分を運んでいた通り道。そのまま食べてオッケー！",
          sub="白い筋は、栄養や水分を\n運んでいた通り道。\nそのまま食べてオッケー！",
          sfx=[(0.9, "pop", {}), (2.2, "pop", {"f0": 500, "f1": 1300})]),
    Scene(outro_draw(outro_subject), 3.0, OUTRO_TELOP, line=OUTRO_LINE, sub=OUTRO_SUB, happy=True,
          jumps=[0.1], sfx=[(0.15 + i * 0.12, "pop", {"f0": 400, "f1": 800, "amp": 0.15}) for i in range(5)]
          + [(0.1, "ding", {"amp": 0.35})], tail=0.9),
]

VIDEO = Video(4, SCENES, "banana.mp4",
              bg={"top": (255, 252, 230), "bottom": (255, 232, 150), "dot": (230, 170, 30, 30)},
              badge_color=(222, 150, 10), telop_stroke=(200, 110, 0), bubble_color=(226, 160, 20), bgm="uke",
              bpm=110)

if __name__ == "__main__":
    VIDEO.render()
