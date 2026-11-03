#!/usr/bin/env python3
"""#2 ブロッコリー「実は『つぼみ』を食べている」"""
import math
import random

from PIL import Image, ImageDraw

from engine import (H, OUTRO_LINE, OUTRO_SUB, OUTRO_TELOP, W, Scene, Video, ball, clamp, draw_sparkles,
                    ease_out_back, ease_out_cubic, label, outro_draw, paste_center, pop_scale, prog, rotated,
                    scaled, soft_shadow, sprite)

random.seed(2)

GREEN_L, GREEN, GREEN_D = (120, 180, 80), (58, 128, 52), (30, 82, 34)
STEM_L, STEM, STEM_D = (214, 232, 160), (170, 206, 116), (120, 160, 70)


def make_broccoli(size):
    """丸ごとのブロッコリー（房＋茎）。"""
    w, h = size, int(size * 1.15)
    img = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = 2
    cx = w
    # 茎と枝
    d.polygon([(cx - 70 * k, h * 1.1), (cx + 70 * k, h * 1.1), (cx + 95 * k, h * 1.95), (cx - 95 * k, h * 1.95)],
              fill=STEM)
    d.polygon([(cx - 50 * k, h * 1.1), (cx - 20 * k, h * 1.1), (cx - 30 * k, h * 1.9), (cx - 70 * k, h * 1.9)],
              fill=STEM_L)
    for sgn in (-1, 1):
        d.polygon([(cx, h * 1.35), (cx + sgn * 260 * k / 2.2, h * 0.95), (cx + sgn * 300 * k / 2.2, h * 1.02),
                   (cx + sgn * 40 * k, h * 1.45)], fill=STEM)
    # 房（大きなこぶを重ねる）
    rng = random.Random(5)
    blobs = [(0, -0.05, 0.36), (-0.42, 0.08, 0.3), (0.42, 0.08, 0.3), (-0.22, -0.3, 0.3), (0.22, -0.3, 0.3),
             (-0.6, -0.12, 0.22), (0.6, -0.12, 0.22), (0, -0.42, 0.26), (-0.25, 0.22, 0.26), (0.25, 0.22, 0.26)]
    blobs.sort(key=lambda b: b[1])
    for bx, by, br in blobs:
        r = int(br * w * 2 * 0.62)
        b = ball(r * 2, GREEN_L, GREEN, GREEN_D, light=(-0.3, -0.5), spec=0.12)
        img.alpha_composite(b, (int(cx + bx * w - r), int(h * 0.72 + by * w - r)))
    # つぼみのつぶつぶ
    tex = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tex)
    alpha = img.getchannel("A")
    for _ in range(4200):
        x, y = rng.uniform(0, img.width - 1), rng.uniform(0, h * 1.25)
        if alpha.getpixel((int(x), int(y))) < 200:
            continue
        r = rng.uniform(5, 9)
        c = (150, 200, 100, 120) if rng.random() < 0.5 else (20, 70, 26, 110)
        td.ellipse((x - r, y - r, x + r, y + r), fill=c)
    img.alpha_composite(tex)
    return img.resize((w, h), Image.LANCZOS)


BROC = make_broccoli(520)
SHADOW = soft_shadow(460, 80)


def scene_hook(frame, lt, sc):
    s = 2.4 - 1.4 * ease_out_cubic(prog(lt, 0.0, 1.6))
    paste_center(frame, SHADOW, W / 2, 1000 + 300 * s, alpha=clamp(1.6 - s))
    paste_center(frame, scaled(BROC, s), W / 2, 1000 + 60 * (s - 1))
    if lt > 1.6:
        q = label("？", 140, stroke_fill=(40, 120, 40))
        s2, a = pop_scale(lt, 1.6)
        paste_center(frame, scaled(q, s2), W / 2 + 290, 760, alpha=a)


# ---- つぼみが花になる
BUD_R = 34
BUDS = []
for row in range(-7, 8):
    for col in range(-7, 8):
        x = col * BUD_R * 1.85 + (BUD_R * 0.92 if row % 2 else 0)
        y = row * BUD_R * 1.6
        if x * x + y * y < 380 ** 2:
            BUDS.append((x, y, random.random()))
BUD_IMG = ball(BUD_R * 2, (130, 190, 90), (62, 136, 56), (28, 80, 32), light=(-0.3, -0.4), spec=0.3)


def make_flower(size):
    def fn(d, k, img):
        c = size * k / 2
        for i in range(4):
            a = i * math.pi / 2 + math.pi / 4
            px, py = c + math.cos(a) * c * 0.48, c + math.sin(a) * c * 0.48
            d.ellipse((px - c * 0.5, py - c * 0.5, px + c * 0.5, py + c * 0.5), fill=(255, 226, 60, 255),
                      outline=(236, 180, 20, 255), width=int(2 * k))
        d.ellipse((c - c * 0.22, c - c * 0.22, c + c * 0.22, c + c * 0.22), fill=(240, 160, 20, 255))
    return sprite(size, size, fn)


FLOWER = make_flower(96)


def scene_buds(frame, lt, sc):
    cx, cy = W / 2, 1000
    zoom = 0.85 + 0.15 * ease_out_cubic(prog(lt, 0, 0.6))
    # 背景の円（房の断面）
    base = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
    ImageDraw.Draw(base).ellipse((40, 40, 860, 860), fill=(40, 100, 40, 255))
    paste_center(frame, scaled(base, zoom), cx, cy)
    for x, y, r in BUDS:
        bloom = prog(lt, 1.8 + r * 2.4, 0.4) if r < 0.45 else 0
        px, py = cx + x * zoom, cy + y * zoom
        if bloom < 1:
            paste_center(frame, scaled(BUD_IMG, zoom * (1 - 0.5 * bloom)), px, py)
        if bloom > 0:
            paste_center(frame, scaled(FLOWER, zoom * ease_out_back(bloom) * 0.9), px, py, alpha=clamp(bloom * 2))
    if lt > 2.0:
        draw_sparkles(frame, lt, cx, cy, 420, 3, n=6)


# ---- 茎を切る
def make_board():
    def fn(d, k, img):
        d.rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=int(40 * k), fill=(222, 178, 120, 255))
        for i in range(9):
            y = (30 + i * 42) * k
            d.line((30 * k, y, img.width - 30 * k, y + 8 * k), fill=(200, 150, 96, 255), width=int(3 * k))
    return sprite(960, 420, fn)


def make_stem_piece(w, h, cut_left=True, cut_right=True):
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((0, 0, ww - 1, hh - 1), radius=int(30 * k), fill=STEM + (255,),
                            outline=STEM_D + (255,), width=int(4 * k))
        d.rectangle((10 * k, hh * 0.2, ww - 10 * k, hh * 0.38), fill=STEM_L + (255,))
        for x, cut in ((0, cut_left), (ww, cut_right)):
            if cut:
                d.ellipse((x - 18 * k, 0, x + 18 * k, hh - 1), fill=(236, 244, 200, 255),
                          outline=STEM_D + (255,), width=int(3 * k))
    return sprite(w, h, fn)


BOARD = make_board()
PIECES = [make_stem_piece(220, 150, i > 0, i < 3) for i in range(4)]


def make_knife():
    def fn(d, k, img):
        d.polygon([(0, 0), (90 * k, 0), (90 * k, 300 * k), (0, 360 * k)], fill=(214, 220, 228, 255),
                  outline=(150, 160, 170, 255))
        d.line((12 * k, 10 * k, 12 * k, 340 * k), fill=(250, 252, 255, 255), width=int(6 * k))
        d.rounded_rectangle((10 * k, -0, 80 * k, 0), radius=4, fill=(0, 0, 0, 0))
    blade = sprite(90, 360, fn)
    handle = sprite(70, 190, lambda d, k, img: d.rounded_rectangle((0, 0, img.width - 1, img.height - 1),
                                                                   radius=int(26 * k), fill=(120, 72, 40, 255)))
    img = Image.new("RGBA", (90, 560), (0, 0, 0, 0))
    img.alpha_composite(handle, (10, 0))
    img.alpha_composite(blade, (0, 190))
    return img


KNIFE = make_knife()
CHOPS = [1.0, 1.7, 2.4]


def scene_chop(frame, lt, sc):
    cx, cy = W / 2, 1060
    paste_center(frame, BOARD, cx, cy)
    n_cut = sum(1 for c in CHOPS if lt >= c + 0.12)
    for i, piece in enumerate(PIECES):
        spread = 0
        for j, c in enumerate(CHOPS):
            if lt >= c + 0.12:
                gap = ease_out_back(prog(lt, c + 0.12, 0.3), 2.2) * 26
                spread += gap if i > j else 0
        x = cx - 330 + i * 220 + spread - 26 * n_cut / 2
        paste_center(frame, piece, x, cy)
    # 包丁の動き
    for j, c in enumerate(CHOPS):
        if c - 0.35 <= lt < c + 0.3:
            p = lt - (c - 0.35)
            down = ease_out_cubic(clamp(p / 0.35))
            up = clamp((p - 0.4) / 0.25)
            y = cy - 620 + 470 * down - 300 * up
            paste_center(frame, KNIFE, cx - 220 + j * 220, y)
            break


# ---- 皮をむいて薄切り
def make_slice(size):
    def fn(d, k, img):
        c = size * k / 2
        d.ellipse((2 * k, 2 * k, size * k - 2 * k, size * k - 2 * k), fill=(232, 242, 186, 255),
                  outline=(150, 190, 90, 255), width=int(5 * k))
        d.ellipse((c * 0.45, c * 0.45, c * 1.55, c * 1.55), fill=(214, 232, 160, 255))
        for i in range(6):
            a = i * math.pi / 3
            d.line((c, c, c + math.cos(a) * c * 0.5, c + math.sin(a) * c * 0.5), fill=(196, 220, 140, 255),
                   width=int(3 * k))
    return sprite(size, size, fn)


SLICE = make_slice(150)
STEM_UP = rotated(make_stem_piece(380, 190, True, False), 90)
SKIN = sprite(STEM_UP.width, STEM_UP.height,
              lambda d, k, img: d.rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=int(30 * k),
                                                    fill=GREEN + (255,), outline=GREEN_D + (255,), width=int(5 * k)))


def make_plate(w, h):
    def fn(d, k, img):
        d.ellipse((0, 0, img.width - 1, img.height - 1), fill=(255, 255, 255, 255), outline=(220, 210, 200, 255),
                  width=int(4 * k))
        d.ellipse((img.width * 0.1, img.height * 0.12, img.width * 0.9, img.height * 0.88),
                  outline=(236, 230, 222, 255), width=int(4 * k))
    return sprite(w, h, fn)


PLATE = make_plate(820, 520)
PEEL = sprite(40, 300, lambda d, k, img: d.rounded_rectangle((0, 0, img.width - 1, img.height - 1),
                                                             radius=int(18 * k), fill=GREEN + (255,)))


def scene_peel(frame, lt, sc):
    cx, cy = W / 2, 1000
    out = ease_out_cubic(prog(lt, 2.3, 0.4))
    if out < 1:
        paste_center(frame, STEM_UP, cx, cy - 80 * out, alpha=1 - out)
        peeled = clamp((lt - 0.5) / 1.4)
        paste_center(frame, SKIN, cx, cy - 80 * out, alpha=(1 - peeled) * (1 - out))
        # 皮が4枚はがれて飛んでいく
        for i in range(4):
            p = prog(lt, 0.5 + i * 0.35, 0.55)
            sgn = -1 if i % 2 == 0 else 1
            if p <= 0:
                x = cx + sgn * (70 + 18 * (i // 2))
                paste_center(frame, PEEL, x, cy, alpha=1 - out)
            elif p < 1:
                x = cx + sgn * (70 + 340 * ease_out_cubic(p))
                y = cy - 200 * math.sin(p * math.pi) + 260 * p * p
                paste_center(frame, rotated(PEEL, sgn * -140 * p), x, y, alpha=(1 - p) * (1 - out))
        if lt > 0.5:
            k = clamp((lt - 0.5) / 1.6)
            paste_center(frame, label("厚めに！", 60, stroke_fill=(40, 120, 40)), cx + 280, cy - 260,
                         alpha=clamp(k * 3) * (1 - out))
    if lt >= 2.3:
        paste_center(frame, PLATE, cx, cy + 40, alpha=clamp((lt - 2.3) * 4))
        for i in range(6):
            s, a = pop_scale(lt, 2.5 + i * 0.16, 0.3)
            if a > 0:
                ang = math.pi + i * math.pi / 5
                x = cx + math.cos(ang) * 230
                y = cy + 30 + math.sin(ang) * 120 + 60
                paste_center(frame, scaled(SLICE, s), x, y, alpha=a)
        s, a = pop_scale(lt, 3.6)
        if a > 0:
            paste_center(frame, scaled(label("甘い！", 90, fill=(255, 250, 200), stroke_fill=(40, 120, 40)), s),
                         cx + 250, cy - 230, alpha=a)
            draw_sparkles(frame, lt, cx, cy + 40, 360, 6, n=5)


# ---- 蒸し器
def make_steamer():
    def fn(d, k, img):
        ww, hh = img.size
        d.rounded_rectangle((0, hh * 0.3, ww - 1, hh - 1), radius=int(60 * k), fill=(214, 170, 100, 255),
                            outline=(170, 120, 60, 255), width=int(6 * k))
        for i in range(3):
            y = hh * (0.45 + i * 0.17)
            d.line((20 * k, y, ww - 20 * k, y), fill=(186, 136, 74, 255), width=int(8 * k))
        d.ellipse((0, 0, ww - 1, hh * 0.6), fill=(230, 196, 130, 255), outline=(170, 120, 60, 255),
                  width=int(6 * k))
        d.ellipse((ww * 0.06, hh * 0.05, ww * 0.94, hh * 0.55), fill=(120, 84, 44, 255))
    return sprite(720, 420, fn)


STEAMER = make_steamer()
SMALL_BROC = make_broccoli(220)
PUFF = sprite(160, 160, lambda d, k, img: d.ellipse((0, 0, img.width - 1, img.height - 1),
                                                   fill=(255, 255, 255, 150)))


def scene_steam(frame, lt, sc):
    cx, cy = W / 2, 1060
    paste_center(frame, STEAMER, cx, cy + 60)
    for i, dx in enumerate((-190, 0, 190, -95, 95)):
        dy = -70 if i < 3 else -130
        paste_center(frame, SMALL_BROC, cx + dx, cy + dy - 20)
    rng = random.Random(11)
    for i in range(10):
        ph = rng.uniform(0, 1)
        p = ((lt / 2.2) + ph) % 1.0
        x = cx + rng.uniform(-260, 260) + math.sin(p * 6 + i) * 30
        y = cy - 160 - p * 520
        paste_center(frame, scaled(PUFF, 0.5 + p), x, y, alpha=0.8 * math.sin(p * math.pi))
    s, a = pop_scale(lt, 1.2)
    if a > 0:
        paste_center(frame, scaled(label("栄養キープ！", 66, stroke_fill=(40, 120, 40)), s), cx + 250, cy - 300,
                     alpha=a)


def outro_subject(frame, cx, cy, s, lt):
    paste_center(frame, SHADOW, cx, cy + 300, alpha=0.8)
    paste_center(frame, scaled(BROC, s * 0.95), cx, cy)


SCENES = [
    Scene(scene_hook, 3.2, "これ、何の部分か\n知ってる？",
          line="ブロッコリーの、このモコモコ、何か知ってる？",
          sub="ブロッコリーのこのモコモコ、\n何か知ってる？", sfx=[(0.1, "whoosh", {"dur": 1.2, "amp": 0.12}),
                                                     (1.6, "pop", {})]),
    Scene(scene_buds, 5.5, "正体は\nつぼみ！",
          line="実はこれ、全部つぼみ！ほうっておくと、黄色い花が咲くんだワン！",
          sub="実はこれ、全部つぼみ！\n放っておくと、黄色い花が\n咲くんだワン！",
          sfx=[(1.8 + i * 0.35, "pop", {"f0": 700, "f1": 1400, "amp": 0.12}) for i in range(7)], jumps=[2.0]),
    Scene(scene_chop, 3.6, "茎は\n捨てないで！", line="そして、捨てがちな茎…",
          sub="そして、捨てがちな茎…", sfx=[(c, "chop", {}) for c in CHOPS]),
    Scene(scene_peel, 5.2, "皮を厚めにむくと\n甘くてシャキシャキ",
          line="皮を厚めにむけば、甘くてシャキシャキ！炒め物にぴったりだよ！",
          sub="皮を厚めにむけば、\n甘くてシャキシャキ！\n炒め物にぴったりだよ！",
          sfx=[(0.5 + i * 0.35, "whoosh", {"dur": 0.3, "amp": 0.15}) for i in range(4)]
          + [(2.5 + i * 0.16, "pop", {"f0": 400, "f1": 800, "amp": 0.15}) for i in range(6)]
          + [(3.6, "ding", {})], jumps=[3.6]),
    Scene(scene_steam, 4.5, "ゆでるより\n蒸す・レンジ！",
          line="ゆでるより、蒸すかレンジのほうが、栄養が逃げにくいよ！",
          sub="ゆでるより、蒸すかレンジの\nほうが、栄養が逃げにくいよ！", sfx=[(1.2, "pop", {})]),
    Scene(outro_draw(outro_subject), 3.0, OUTRO_TELOP, line=OUTRO_LINE, sub=OUTRO_SUB, happy=True,
          jumps=[0.1], sfx=[(0.1, "ding", {"amp": 0.35}), (1.0, "pop", {"f0": 500, "f1": 1300})], tail=0.9),
]

VIDEO = Video(2, SCENES, "broccoli.mp4",
              bg={"top": (244, 252, 236), "bottom": (204, 234, 184), "dot": (90, 160, 60, 30)},
              badge_color=(70, 150, 60), telop_stroke=(40, 120, 40), bubble_color=(80, 160, 60), bgm="fresh")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        print(VIDEO.preview([float(x) for x in sys.argv[3:]], sys.argv[2]))
    else:
        VIDEO.render()
