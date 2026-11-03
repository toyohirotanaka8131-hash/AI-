#!/usr/bin/env python3
"""シリーズ全動画のサムネイル（リール表紙用 1080x1920）を作る。

プロフィールの一覧では中央の 3:4（1080x1440, 上下240pxずつ切れる）だけが見えるので、
文字とキャラクターはその範囲に収める。出力: video/out/thumbs/thumb_XX.png
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402

OUT = os.path.join(E.HERE, "out", "thumbs")


def sunburst(color, alpha=60, rays=18):
    img = Image.new("RGBA", (E.W, E.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = E.W / 2, 1020
    R = 1600
    for i in range(rays):
        a0 = i * 2 * math.pi / rays
        a1 = a0 + math.pi / rays
        d.polygon([(cx, cy), (cx + math.cos(a0) * R, cy + math.sin(a0) * R),
                   (cx + math.cos(a1) * R, cy + math.sin(a1) * R)], fill=color + (alpha,))
    glow = Image.new("RGBA", (E.W, E.H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((cx - 420, cy - 420, cx + 420, cy + 420), fill=(255, 255, 245, 200))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(80)))
    return img


def number_badge(n, color):
    def fn(d, k, img):
        s = img.width
        d.ellipse((0, 0, s - 1, s - 1), fill=color + (255,), outline=(255, 255, 255, 255), width=int(10 * k))
    img = E.sprite(190, 190, fn)
    t = E.text_img(f"#{n}", 88, fill=(255, 255, 255))
    img.alpha_composite(t, ((img.width - t.width) // 2, (img.height - t.height) // 2 - 4))
    return img


def make_thumb(n, video, title, subject_fn, ray_color):
    frame = video.bg.copy()
    frame.alpha_composite(sunburst(ray_color))
    subject_fn(frame)
    # タイトル（大きく・太く）
    sh = E.text_img(title, 140, fill=(90, 40, 0), stroke=22, stroke_fill=(90, 40, 0), spacing=20)
    tt = E.text_img(title, 140, fill=(255, 255, 255), stroke=22, stroke_fill=video.telop_stroke, spacing=20)
    fit = min(1.0, (E.W - 50) / tt.width)      # 長いタイトルは横幅に収まるよう縮める
    E.paste_center(frame, E.scaled(sh, fit), E.W / 2 + 8, 560 + 10, alpha=0.45)
    E.paste_center(frame, E.scaled(tt, fit), E.W / 2, 560)
    E.paste_center(frame, video.badge, E.W / 2, 330)
    # コロ（大きめ・にっこり）
    dog = E.scaled(E.dog_sprite(4, "happy"), 1.55)
    E.paste_center(frame, E.rotated(dog, 6), 230, 1470)
    E.paste_center(frame, number_badge(n, video.telop_stroke), 900, 1520)
    E.draw_sparkles(frame, 0.37, E.W / 2, 1020, 430, n, n=8)
    return frame.convert("RGB")


def main():
    os.makedirs(OUT, exist_ok=True)
    import make_banana as ban
    import make_broccoli as bro
    import make_ichigo as ich
    import make_mikan as mik
    import make_tomato as tom

    mik_video = E.Video(1, [], "mikan.mp4", badge_color=(236, 110, 20), telop_stroke=(214, 84, 0))
    side = mik.make_side_mandarin(600)
    top = mik.make_top_mandarin(560)

    def s_mikan(f):
        E.paste_center(f, E.soft_shadow(520, 80), 640, 1330)
        E.paste_center(f, E.scaled(side, 1.15), 640, 1050)
        E.paste_center(f, E.rotated(E.scaled(top, 0.55), 10), 300, 1000)
        d = ImageDraw.Draw(f)
        for i, (px, py) in enumerate(mik.dot_positions(300, 1000, 0.55 * 560 / mik.TOP_D)):
            d.ellipse((px - 6, py - 6, px + 6, py + 6), fill=(255, 253, 240))
        E.paste_center(f, E.label("？", 170, stroke_fill=(214, 84, 0), stroke=14), 960, 1010)

    def s_broc(f):
        E.paste_center(f, bro.SHADOW, E.W / 2 + 80, 1360)
        E.paste_center(f, E.scaled(bro.BROC, 1.3), E.W / 2 + 80, 1030)
        E.paste_center(f, E.scaled(bro.FLOWER, 1.4), 300, 900)
        E.paste_center(f, E.scaled(bro.FLOWER, 1.0), 220, 1060)
        E.paste_center(f, E.label("？", 170, stroke_fill=(40, 120, 40), stroke=14), 960, 1010)

    def s_ichigo(f):
        E.paste_center(f, E.soft_shadow(720, 80), E.W / 2, 1340)
        E.paste_center(f, E.rotated(E.scaled(ich.BERRY, 1.05), 12), E.W / 2 - 180, 1030)
        E.paste_center(f, E.rotated(E.scaled(ich.HALF, 1.05), -10), E.W / 2 + 210, 1050)
        E.paste_center(f, E.label("実はどれ？", 70, fill=(255, 245, 170), stroke_fill=(200, 30, 70)), 800, 1330)

    def s_banana(f):
        img = ban.BIG_BAN.copy()
        img.alpha_composite(ban.BIG_SPOTS)
        E.paste_center(f, ban.SHADOW, E.W / 2, 1300)
        E.paste_center(f, E.rotated(E.scaled(img, 1.05), -8), E.W / 2 + 40, 1050)
        E.paste_center(f, E.label("STOP！", 110, fill=(255, 255, 255), stroke_fill=(230, 60, 60), stroke=14),
                       830, 1290)

    def s_tomato(f):
        E.paste_center(f, tom.SHADOW, E.W / 2 + 200, 1320)
        E.paste_center(f, E.scaled(tom.TOMATO, 1.0), E.W / 2 + 200, 1110)
        bottom = tom.BOTTOM.copy()
        d = ImageDraw.Draw(bottom)
        c = bottom.width / 2
        for i in range(7):
            a = -math.pi / 2 + i * 2 * math.pi / 7
            d.line((c + math.cos(a) * 20, c + math.sin(a) * 20, c + math.cos(a) * 270, c + math.sin(a) * 270),
                   fill=(255, 240, 230, 240), width=14)
        d.ellipse((c - 24, c - 24, c + 24, c + 24), fill=(160, 110, 50))
        E.paste_center(f, E.scaled(bottom, 0.68), 380, 960)
        E.paste_center(f, E.label("★", 140, fill=(255, 236, 90), stroke_fill=(200, 120, 0)), 600, 760)

    items = [
        (1, mik_video, "むく前に\n房の数わかる？", s_mikan, (255, 170, 60)),
        (2, bro.VIDEO, "モコモコの\n正体は？", s_broc, (120, 200, 90)),
        (3, ich.VIDEO, "いちごの実は\nどこ？", s_ichigo, (255, 130, 150)),
        (4, ban.VIDEO, "茶色い点は\n捨てないで！", s_banana, (255, 200, 60)),
        (5, tom.VIDEO, "甘いトマトは\nお尻でわかる", s_tomato, (255, 120, 90)),
    ]
    # #6 以降：各スクリプトの THUMB と thumb_subject を使う
    import importlib
    for n, name in enumerate(["make_ringo", "make_ninjin", "make_kiwi", "make_tamanegi", "make_suika"], start=6):
        mod = importlib.import_module(name)
        title, ray = mod.THUMB
        items.append((n, mod.VIDEO, title, mod.thumb_subject, ray))
    thumbs = []
    for n, video, title, fn, ray in items:
        img = make_thumb(n, video, title, fn, ray)
        path = os.path.join(OUT, f"thumb_{n:02d}.png")
        img.save(path, optimize=True)
        thumbs.append(img)
        print("wrote", path)
    # 一覧（プロフィールでの見え方：中央3:4）
    cw, ch = 360, 480
    rows = (len(thumbs) + 2) // 3
    sheet = Image.new("RGB", (cw * 3 + 40, ch * rows + 10 * (rows + 1)), (250, 250, 250))
    for i, img in enumerate(thumbs):
        crop = img.crop((0, 240, 1080, 1680)).resize((cw, ch), Image.LANCZOS)
        sheet.paste(crop, (10 + (i % 3) * (cw + 10), 10 + (i // 3) * (ch + 10)))
    path = os.path.join(OUT, "grid_preview.png")
    sheet.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
