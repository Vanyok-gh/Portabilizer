"""TGA -> PNG: эталонный декодер и PowerShell-блок. Запуск: python tests/test_tga.py"""
import struct, sys, tempfile, zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pzp_tga as T

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def hdr(w, h, bpp, itype=2, desc=0, idlen=0):
    return bytes([idlen, 0, itype, 0, 0, 0, 0, 0, 0, 0, 0, 0]) + struct.pack("<HH", w, h) + bytes([bpp, desc])

def png_pixels(png, w, h):
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat = 8, b""
    while pos < len(png):
        ln = struct.unpack(">I", png[pos:pos + 4])[0]; tag = png[pos + 4:pos + 8]; body = png[pos + 8:pos + 8 + ln]
        assert struct.unpack(">I", png[pos + 8 + ln:pos + 12 + ln])[0] == zlib.crc32(tag + body) & 0xFFFFFFFF
        if tag == b"IDAT": idat += body
        pos += 12 + ln
    raw = zlib.decompress(idat); rows = []
    for y in range(h):
        assert raw[y * (w * 4 + 1)] == 0
        rows.append(raw[y * (w * 4 + 1) + 1:(y + 1) * (w * 4 + 1)])
    return rows

# 2x2, 24 бита, начало снизу: нижняя строка в файле первая. BGR
red, green, blue, white = (0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 255)
body = bytes(blue + white + red + green)           # нижняя строка: blue, white; верхняя: red, green
w, h, rgba = T.decode_tga(hdr(2, 2, 24) + body)
check((w, h) == (2, 2), "размер")
check(rgba[:8] == bytes([255, 0, 0, 255, 0, 255, 0, 255]), "верхняя строка red, green (перевёрнуто правильно)")
check(rgba[8:] == bytes([0, 0, 255, 255, 255, 255, 255, 255]), "нижняя строка blue, white")
# начало сверху (бит 0x20): порядок как в файле
w, h, rgba2 = T.decode_tga(hdr(2, 2, 24, desc=0x20) + body)
check(rgba2[:4] == bytes([0, 0, 255, 255]), "top-left: первая строка в файле остаётся первой")
# 32 бита, нулевая альфа везде -> непрозрачно; реальная альфа сохраняется
b32 = bytes([1, 2, 3, 0] * 4)
check(set(T.decode_tga(hdr(2, 2, 32) + b32)[2][3::4]) == {255}, "нулевая альфа -> 255")
b32b = bytes([1, 2, 3, 128, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0])
check(T.decode_tga(hdr(2, 2, 32) + b32b)[2][3::4].count(128) == 1, "настоящая альфа сохранена")
# RLE: пакет повторов 3 пикселя + сырой пакет 1 пиксель (2x2)
rle = bytes([0x80 | 2]) + bytes(red) + bytes([0]) + bytes(green)
w, h, r3 = T.decode_tga(hdr(2, 2, 24, itype=10, desc=0x20) + rle)
check(r3 == bytes([255, 0, 0, 255] * 3 + [0, 255, 0, 255]), "RLE")
# поле ID пропускается
w, h, r4 = T.decode_tga(hdr(1, 1, 24, idlen=3) + b"abc" + bytes(red))
check(r4 == bytes([255, 0, 0, 255]), "ID-поле пропущено")
# мусор и плохие файлы
for bad, m in ((b"", "пусто"), (hdr(2, 2, 24)[:10], "обрезан заголовок"), (hdr(2, 2, 24) + b"xx", "мало данных"),
               (hdr(2, 2, 8), "8 бит"), (hdr(2, 2, 24, itype=1), "палитра"), (hdr(0, 5, 24), "нулевой размер"),
               (hdr(20000, 20000, 24), "слишком большой"), (hdr(2, 2, 24, itype=10) + bytes([0x80]), "RLE оборван")):
    try:
        T.decode_tga(bad); ok = False
    except ValueError:
        ok = True
    check(ok, "ValueError: " + m)
# PNG
png = T.encode_png(2, 2, rgba)
rows = png_pixels(png, 2, 2)
check(rows[0] == rgba[:8] and rows[1] == rgba[8:], "PNG содержит те же пиксели")
with tempfile.TemporaryDirectory() as d:
    d = Path(d); (d / "a.tga").write_bytes(hdr(2, 2, 24) + body)
    T.tga_to_png(d / "a.tga", d / "a.png")
    check((d / "a.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and (d / "a.tga").exists(), "tga_to_png: png создан, tga на месте")

# PowerShell-блок в Portable.ps1
import portabilizer_v8 as P
ps = P.PORTABLE_PS
check("#SHOTS#" not in ps and "PzTga" in ps, "блок вставлен в Portable.ps1")
check(ps.index("-Wait") < ps.index("Screenshots_PNG.txt") < ps.index("Dismount-DiskImage -ImagePath $m"), "конвертация после выхода из игры и до размонтирования")
check("$gameStart = Get-Date" in ps and ps.index("$gameStart") < ps.index("-Wait"), "время старта игры запоминается до запуска")
check("@'\n" in ps and "\n'@" in ps and ps.count("@'") == 1, "here-string C# корректно закрыт")
check("Remove-Item" in ps.split("PzTga]::Convert")[1].split("\n")[0], "битый png удаляется при ошибке")
check("Delete" not in ps.split("Screenshots_PNG.txt")[1] and "Remove-Item -LiteralPath $t.FullName" not in ps, "оригинальные tga не удаляются")
check(ps.count("{") == ps.count("}"), "скобки сбалансированы")
# write_portable_ps создаёт флаг только при включённой опции и работает без Discs/Registry
with tempfile.TemporaryDirectory() as d:
    d = Path(d); logs = []
    P.SHOT_OPTIONS["png"] = False
    check(P.write_portable_ps(d, logs.append) is False and not (d / "Portable.ps1").exists(), "опция выключена, Portable.ps1 не нужен")
    P.SHOT_OPTIONS["png"] = True
    check(P.write_portable_ps(d, logs.append) is True and (d / "Screenshots_PNG.txt").is_file(), "опция включена: Portable.ps1 и флаг созданы")
    check(any("tga" in x for x in logs), "в логе сказано про скриншоты")
    P.SHOT_OPTIONS["png"] = False
print(f"test_tga: OK ({n} проверок)")
