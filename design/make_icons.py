"""Чистит шахматный фон у присланных иконок и собирает PNG/ICO. Запуск: python make_icons.py <папка с исходниками> <куда>"""
import sys, glob, os
from PIL import Image
from collections import deque

SRC = {"red": "f0077604", "blue": "27855a23", "launcher_smooth": "e24711ff"}

def is_bg(p):
    r, g, b = p[:3]
    return abs(r-g) < 6 and abs(g-b) < 6 and r >= 200      # 209 / 237 серые клетки

def strip_bg(im):
    im = im.convert("RGBA"); w, h = im.size; px = im.load()
    seen = bytearray(w*h); q = deque()
    for x in range(w):
        q += [(x, 0), (x, h-1)]
    for y in range(h):
        q += [(0, y), (w-1, y)]
    while q:
        x, y = q.popleft()
        if not (0 <= x < w and 0 <= y < h) or seen[y*w+x]: continue
        if not is_bg(px[x, y]): continue
        seen[y*w+x] = 1; px[x, y] = (0, 0, 0, 0)
        q += [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
    return im

def crop_square(im, pad=0.04):
    bb = im.getbbox(); im = im.crop(bb); w, h = im.size; s = int(max(w, h)*(1+pad*2))
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0)); out.paste(im, ((s-w)//2, (s-h)//2)); return out

def native_pixels(im):
    """Пиксель-арт, увеличенный блоками: находим размер блока и возвращаем настоящую сетку."""
    px = im.load(); w, h = im.size
    best = 1
    for k in range(2, 12):
        ok = 0; tot = 0
        for y in range(0, h-k, k):
            for x in range(0, w-k, k):
                tot += 1; ok += px[x, y] == px[x+k-1, y+k-1]
        if tot and ok/tot > 0.97: best = k
    return im.resize((w//best, h//best), Image.NEAREST), best

def defringe(im):
    """убирает светло-серую кайму от шахматки вокруг контура"""
    px = im.load(); w, h = im.size
    for _ in range(3):
        kill = []
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a and abs(r-g) < 22 and abs(g-b) < 22 and r > 150:
                    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                        xx, yy = x+dx, y+dy
                        if not (0 <= xx < w and 0 <= yy < h) or px[xx, yy][3] == 0:
                            kill.append((x, y)); break
        for x, y in kill: px[x, y] = (0, 0, 0, 0)
    return im

def feather_pixels(im, n=24):
    im = crop_square(defringe(im), 0.0)
    sm = im.resize((n, n), Image.BOX)
    a = sm.getchannel("A").point(lambda v: 255 if v > 120 else 0)
    q = sm.convert("RGB").quantize(10, dither=Image.NONE).convert("RGBA"); q.putalpha(a); return q

def pixel_cabinet():
    """Пиксельный шкаф с зелёным пером, 32x32, нарисован по клеткам"""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0)); P = im.load()
    K=(30,30,34,255); G1=(120,130,140,255); G2=(165,175,184,255); G3=(205,212,218,255)
    Y=(240,212,120,255); Y2=(205,170,80,255); W=(250,250,250,255)
    def rect(x0,y0,x1,y1,c):
        for y in range(y0,y1+1):
            for x in range(x0,x1+1): P[x,y]=c
    rect(6,2,21,29,K); rect(7,3,20,28,G2)           # корпус
    rect(17,3,20,28,G1)                              # боковая грань (тень)
    rect(7,3,16,3,G3)
    rect(8,5,15,13,G3); rect(8,5,15,5,W)             # верхний ящик
    rect(10,8,13,9,K); rect(11,8,12,8,W)             # ручка
    rect(8,14,15,14,K)                               # шов
    rect(7,15,16,18,Y); rect(7,15,16,15,Y2)         # папки
    rect(8,19,15,27,G3); rect(8,19,15,19,W)         # нижний ящик
    rect(10,22,13,23,K); rect(11,22,12,22,W)
    f=(88,190,90,255); f2=(40,130,60,255)           # перо
    for (x,y) in [(24,20),(25,19),(26,19),(25,20),(26,20),(27,20),(24,21),(25,21),(26,21),(27,21),(28,21),
                  (24,22),(25,22),(26,22),(27,22),(28,22),(25,23),(26,23),(27,23),(26,24),(27,24)]: P[x,y]=f
    for (x,y) in [(25,21),(26,22),(27,23),(26,25),(25,26),(25,27),(24,28)]: P[x,y]=f2
    for (x,y) in [(23,20),(24,19),(25,18),(26,18),(27,19),(28,20),(29,21),(29,22),(28,23),(28,24),(27,25),(23,21),(23,22),(24,23),(25,24),(26,26),(25,25),(24,27),(24,29),(23,28)]:
        if P[x,y][3]==0: P[x,y]=K
    return im

def pixelate(im, n=32, colors=24):
    sm = im.resize((n, n), Image.LANCZOS)
    a = sm.getchannel("A").point(lambda v: 255 if v > 110 else 0)
    q = sm.convert("RGB").quantize(colors, dither=Image.NONE).convert("RGB")
    q = q.convert("RGBA"); q.putalpha(a); return q

def main(src, dst):
    os.makedirs(dst, exist_ok=True); res = {}
    for name, key in SRC.items():
        im = strip_bg(Image.open(glob.glob(os.path.join(src, key+"*"))[0])); res[name] = crop_square(im)
    for n in ("red", "blue"):                         # настоящая пиксельная сетка
        res[n+"_pixel"] = crop_square(defringe(strip_bg(Image.open(glob.glob(os.path.join(src, SRC[n]+"*"))[0]))), 0.02)
    res["launcher_pixel"] = pixel_cabinet()
    for n, im in res.items(): im.save(os.path.join(dst, n+".png"))
    return res

if __name__ == "__main__": main(*sys.argv[1:3])
