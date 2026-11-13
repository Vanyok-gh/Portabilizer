"""Скриншоты игр в TGA -> PNG после выхода из игры (v10.4). Игра при этом уже закрыта, оригиналы не удаляются.
Здесь: эталонный декодер на Python (проверяется тестами) и PowerShell-блок для Portable.ps1 с тем же алгоритмом на C#
(Windows PowerShell компилирует его сам, ничего ставить не нужно). Любая ошибка в блоке = просто нет конвертации."""
import struct
import zlib

MAX_SIDE = 16384


def decode_tga(data: bytes):
    """TGA (truecolor 24/32 бит, без сжатия и RLE, любое начало координат) -> (w, h, bytes RGBA сверху вниз)."""
    if len(data) < 18:
        raise ValueError("файл короче заголовка")
    idlen, cmtype, itype = data[0], data[1], data[2]
    w, h = struct.unpack_from("<HH", data, 12)
    bpp, desc = data[16], data[17]
    if cmtype != 0 or itype not in (2, 10):
        raise ValueError("поддерживается только truecolor (тип 2 и 10)")
    if bpp not in (24, 32):
        raise ValueError("поддерживается 24 и 32 бита")
    if not (0 < w <= MAX_SIDE and 0 < h <= MAX_SIDE):
        raise ValueError("странный размер")
    px = bpp // 8
    pos = 18 + idlen
    total = w * h
    raw = bytearray()
    if itype == 2:
        raw = data[pos:pos + total * px]
        if len(raw) < total * px:
            raise ValueError("данных меньше, чем нужно")
    else:
        while len(raw) < total * px:
            if pos >= len(data):
                raise ValueError("RLE оборвался")
            hdr = data[pos]; pos += 1
            n = (hdr & 0x7F) + 1
            if hdr & 0x80:
                chunk = data[pos:pos + px]; pos += px
                if len(chunk) < px:
                    raise ValueError("RLE оборвался")
                raw += chunk * n
            else:
                chunk = data[pos:pos + n * px]; pos += n * px
                if len(chunk) < n * px:
                    raise ValueError("RLE оборвался")
                raw += chunk
        raw = raw[:total * px]
    out = bytearray(total * 4)
    all_zero_alpha = True
    for i in range(total):
        b, g, r = raw[i * px], raw[i * px + 1], raw[i * px + 2]
        a = raw[i * px + 3] if px == 4 else 255
        if a:
            all_zero_alpha = False
        out[i * 4:i * 4 + 4] = bytes((r, g, b, a))
    if all_zero_alpha:                      # у игровых скриншотов альфа часто нулевая: иначе картинка прозрачная
        out[3::4] = b"\xff" * total
    if not desc & 0x20:                     # начало снизу: переворачиваем
        rows = [bytes(out[y * w * 4:(y + 1) * w * 4]) for y in range(h)]
        out = bytearray(b"".join(reversed(rows)))
    return w, h, bytes(out)


def encode_png(w: int, h: int, rgba: bytes) -> bytes:
    def chunk(tag, body):
        c = struct.pack(">I", len(body)) + tag + body
        return c + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def tga_to_png(src, dst):
    with open(src, "rb") as f:
        w, h, rgba = decode_tga(f.read())
    with open(dst, "wb") as f:
        f.write(encode_png(w, h, rgba))


# Тот же алгоритм на C#. Компилируется Add-Type внутри PowerShell; System.Drawing есть в Windows PowerShell 5.1.
CSHARP = r"""
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
public static class PzTga {
    public static bool Convert(string src, string dst) {
        byte[] d = File.ReadAllBytes(src);
        if (d.Length < 18) return false;
        int idlen = d[0], cm = d[1], it = d[2];
        int w = d[12] | (d[13] << 8), h = d[14] | (d[15] << 8);
        int bpp = d[16], desc = d[17];
        if (cm != 0 || (it != 2 && it != 10) || (bpp != 24 && bpp != 32)) return false;
        if (w <= 0 || h <= 0 || w > 16384 || h > 16384) return false;
        int px = bpp / 8, pos = 18 + idlen, total = w * h;
        byte[] raw = new byte[total * px];
        if (it == 2) {
            if (d.Length - pos < raw.Length) return false;
            Buffer.BlockCopy(d, pos, raw, 0, raw.Length);
        } else {
            int n = 0;
            while (n < raw.Length) {
                if (pos >= d.Length) return false;
                int hdr = d[pos++];
                int cnt = (hdr & 0x7F) + 1;
                if ((hdr & 0x80) != 0) {
                    if (pos + px > d.Length) return false;
                    for (int i = 0; i < cnt && n < raw.Length; i++) { Buffer.BlockCopy(d, pos, raw, n, px); n += px; }
                    pos += px;
                } else {
                    int len = cnt * px;
                    if (pos + len > d.Length) return false;
                    int take = Math.Min(len, raw.Length - n);
                    Buffer.BlockCopy(d, pos, raw, n, take); n += take; pos += len;
                }
            }
        }
        bool anyAlpha = false;
        if (px == 4) for (int i = 0; i < total; i++) if (raw[i * 4 + 3] != 0) { anyAlpha = true; break; }
        bool top = (desc & 0x20) != 0;
        using (Bitmap bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb)) {
            BitmapData bd = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
            try {
                byte[] row = new byte[w * 4];
                for (int y = 0; y < h; y++) {
                    int sy = top ? y : h - 1 - y;
                    for (int x = 0; x < w; x++) {
                        int s = (sy * w + x) * px;
                        row[x * 4] = raw[s]; row[x * 4 + 1] = raw[s + 1]; row[x * 4 + 2] = raw[s + 2];
                        row[x * 4 + 3] = (px == 4 && anyAlpha) ? raw[s + 3] : (byte)255;
                    }
                    System.Runtime.InteropServices.Marshal.Copy(row, 0, new IntPtr(bd.Scan0.ToInt64() + (long)y * bd.Stride), row.Length);
                }
            } finally { bmp.UnlockBits(bd); }
            bmp.Save(dst, ImageFormat.Png);
        }
        return true;
    }
}
"""

# Вставляется в Portable.ps1 после выхода из игры. Включается файлом Screenshots_PNG.txt рядом с Launch.bat
# (удалите файл, и конвертации не будет). Берутся только TGA, созданные во время этой игры, не глубже 2 уровней
# от рабочей папки игры. Оригиналы остаются. Лимит по времени 60 секунд, низкий приоритет.
PS_BLOCK = r"""
$flag = Join-Path $Root 'Screenshots_PNG.txt'
if (Test-Path -LiteralPath $flag) {
    try {
        [Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
        Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
""" + CSHARP.strip("\n") + r"""
'@
        $clock = [Diagnostics.Stopwatch]::StartNew()
        $work = Join-Path $Root $Dir
        $n = 0
        foreach ($t in (Get-ChildItem -LiteralPath $work -Filter *.tga -Recurse -Depth 2 -ErrorAction SilentlyContinue)) {
            if ($clock.Elapsed.TotalSeconds -gt 60) { break }
            if ($t.LastWriteTime -lt $gameStart.AddMinutes(-1)) { continue }
            $png = [IO.Path]::ChangeExtension($t.FullName, '.png')
            if (Test-Path -LiteralPath $png) { continue }
            try { if ([PzTga]::Convert($t.FullName, $png)) { $n++ } } catch { Remove-Item -LiteralPath $png -ErrorAction SilentlyContinue }
        }
        if ($n) { Write-Host "Screenshots converted to PNG: $n (the .tga files are kept)" }
    } catch { Write-Host "Screenshot conversion skipped: $($_.Exception.Message)" }
}
"""
