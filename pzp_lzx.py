"""Распаковка CAB со сжатием LZX (то, что лежит в vcredist.msi, merge-модулях и exe-пакетах Visual C++).

Чистый Python, без внешних программ: expand.exe на Windows этот вид cab тоже читает, но Portabilizer
собирает наборы библиотек (и читает старые vcredist) в любой системе, поэтому нужен свой разборщик.
Алгоритм: LZX как в cab (кадры по 32768 байт, окно 2^15..2^21, E8-преобразование вызовов)."""
import struct

FRAME = 32768
MIN_MATCH = 2
SLOTS = {15: 30, 16: 32, 17: 34, 18: 36, 19: 38, 20: 42, 21: 50}


class LzxError(Exception):
    pass


def _tables():
    extra = []
    j = 0
    for i in range(0, 52, 2):
        extra += [j, j]
        if i != 0 and j < 17:
            j += 1
    base = [0]
    for i in range(1, 52):
        base.append(base[-1] + (1 << extra[i - 1]))
    return extra, base


EXTRA, BASE = _tables()


class _Bits:
    """Чтение 16-битных слов (младший байт первым), биты от старшего."""
    __slots__ = ("d", "p", "buf", "n")

    def __init__(self, data):
        self.d = data
        self.p = 0
        self.buf = 0
        self.n = 0

    def need(self, k):
        while self.n < k:
            if self.p + 1 < len(self.d):
                w = self.d[self.p] | (self.d[self.p + 1] << 8)
            elif self.p < len(self.d):
                w = self.d[self.p]
            else:
                w = 0
            self.p += 2
            self.buf = (self.buf << 16) | w
            self.n += 16

    def peek(self, k):
        self.need(k)
        return (self.buf >> (self.n - k)) & ((1 << k) - 1)

    def skip(self, k):
        self.n -= k
        self.buf &= (1 << self.n) - 1

    def read(self, k):
        if k == 0:
            return 0
        v = self.peek(k)
        self.skip(k)
        return v

    def to_bytes(self):
        """Выравнивание перед несжатым блоком: сбрасываем остаток текущего слова, а если биты кончились
        ровно на границе слова - пропускаем целое слово (дополнение 1-16 бит). Дальше идут обычные байты."""
        if self.n == 0:
            self.p += 2
        self.buf = 0
        self.n = 0

    def raw(self, k):
        v = self.d[self.p:self.p + k]
        self.p += k
        return v


def _build(lengths, maxbits=16):
    """Таблица декодирования: список из 2^maxbits элементов (символ << 5 | длина) или None."""
    size = 1 << maxbits
    table = [0] * size
    count = [0] * (maxbits + 2)
    for l in lengths:
        if l:
            count[l] += 1
    # канонические коды: по возрастанию длины, внутри - по номеру символа
    code = 0
    first = [0] * (maxbits + 2)
    for l in range(1, maxbits + 1):
        code = (code + count[l - 1]) << 1 if l > 1 else 0
        first[l] = code
    for sym, l in enumerate(lengths):
        if not l:
            continue
        c = first[l]
        first[l] += 1
        lo = c << (maxbits - l)
        hi = (c + 1) << (maxbits - l)
        if hi > size:
            raise LzxError("неверное дерево Хаффмана")
        table[lo:hi] = [(sym << 5) | l] * (hi - lo)
    return table


def _sym(bits, table, maxbits=16):
    v = table[bits.peek(maxbits)]
    if not v:
        raise LzxError("неверный код Хаффмана")
    bits.skip(v & 31)
    return v >> 5


def _e8(buf, curpos, filesize):
    data = bytearray(buf)
    n = len(data) - 10
    i = 0
    while i < n:
        if data[i] != 0xE8:
            i += 1
            continue
        a = int.from_bytes(data[i + 1:i + 5], "little", signed=True)
        if -(curpos + i) <= a < filesize:
            rel = a - (curpos + i) if a >= 0 else a + filesize
            data[i + 1:i + 5] = (rel & 0xFFFFFFFF).to_bytes(4, "little")
        i += 5
    return bytes(data)


class Decoder:
    def __init__(self, window_bits):
        if window_bits not in SLOTS:
            raise LzxError(f"размер окна 2^{window_bits} не поддерживается")
        self.slots = SLOTS[window_bits]
        self.main_n = 256 + 8 * self.slots
        self.out = bytearray()
        self.R = [1, 1, 1]
        self.main_len = [0] * self.main_n
        self.len_len = [0] * 249
        self.header = False
        self.filesize = 0
        self.btype = 0
        self.remaining = 0
        self.main_t = self.len_t = self.al_t = None
        self.frame_no = 0
        self.produced = 0
        self.blen = 0

    def _read_lengths(self, bits, lens, first, last):
        pre = [bits.read(4) for _ in range(20)]
        pt = _build(pre, 16)
        x = first
        while x < last:
            z = _sym(bits, pt)
            if z == 17:
                run = bits.read(4) + 4
                for _ in range(run):
                    lens[x] = 0
                    x += 1
            elif z == 18:
                run = bits.read(5) + 20
                for _ in range(run):
                    lens[x] = 0
                    x += 1
            elif z == 19:
                run = bits.read(1) + 4
                z = _sym(bits, pt)
                z = (lens[x] - z + 17) % 17
                for _ in range(run):
                    lens[x] = z
                    x += 1
            else:
                lens[x] = (lens[x] - z + 17) % 17
                x += 1

    def frame(self, data, size):
        """Распаковывает один кадр (данные одного CFDATA) в size байт."""
        bits = _Bits(data)
        out = self.out
        start = self.produced
        target = start + size
        if not self.header:
            if bits.read(1):
                hi = bits.read(16)
                lo = bits.read(16)
                self.filesize = (hi << 16) | lo
            self.header = True
        while len(out) < target:
            if self.remaining == 0:
                self.btype = bits.read(3)
                hi = bits.read(16)
                lo = bits.read(8)
                self.remaining = (hi << 8) | lo
                self.blen = self.remaining
                if self.btype in (1, 2):
                    if self.btype == 2:
                        al = [bits.read(3) for _ in range(8)]
                        self.al_t = _build(al, 7 if max(al) <= 7 else 16)
                        self.al_bits = 7 if max(al) <= 7 else 16
                    self._read_lengths(bits, self.main_len, 0, 256)
                    self._read_lengths(bits, self.main_len, 256, self.main_n)
                    self.main_t = _build(self.main_len, 16)
                    self._read_lengths(bits, self.len_len, 0, 249)
                    self.len_t = _build(self.len_len, 16)
                elif self.btype == 3:
                    bits.to_bytes()
                    r = bits.raw(12)
                    self.R = list(struct.unpack("<III", r))
                else:
                    raise LzxError("неизвестный тип блока LZX")
            run = min(self.remaining, target - len(out))
            if self.btype == 3:
                out += bits.raw(run)
                self.remaining -= run
                if self.remaining == 0 and (self.blen & 1):
                    bits.raw(1)                  # байт добивки до чётной длины
                continue
            left = run
            while left > 0:
                m = _sym(bits, self.main_t)
                if m < 256:
                    out.append(m)
                    left -= 1
                    continue
                m -= 256
                length = m & 7
                slot = m >> 3
                if length == 7:
                    length += _sym(bits, self.len_t)
                length += MIN_MATCH
                R = self.R
                if slot == 0:
                    off = R[0]
                elif slot == 1:
                    off = R[1]
                    R[1] = R[0]
                    R[0] = off
                elif slot == 2:
                    off = R[2]
                    R[2] = R[0]
                    R[0] = off
                else:
                    eb = EXTRA[slot]
                    if self.btype == 2 and eb >= 3:
                        v = bits.read(eb - 3) if eb > 3 else 0
                        off = BASE[slot] - 2 + (v << 3) + _sym(bits, self.al_t, self.al_bits)
                    elif eb > 0:
                        off = BASE[slot] - 2 + bits.read(eb)
                    else:
                        off = BASE[slot] - 2
                    R[2] = R[1]
                    R[1] = R[0]
                    R[0] = off
                if off > len(out):
                    raise LzxError("ссылка за пределы окна")
                if off >= length:
                    p = len(out) - off
                    out += out[p:p + length]
                else:
                    for _ in range(length):
                        out.append(out[-off])
                left -= length
            self.remaining -= run
            if left < 0:
                # совпадение вышло за границу блока или кадра: учтём лишнее
                self.remaining += left
                if self.remaining < 0:
                    raise LzxError("совпадение пересекает границу блока")
        res = bytes(out[start:target])
        self.produced = target                  # хвост совпадения за границей кадра войдёт в следующий
        if self.filesize and self.frame_no < 32768 and len(res) > 10:
            res = _e8(res, start, self.filesize)     # окно хранит данные без преобразования
        self.frame_no += 1
        return res


def decompress(frames, window_bits):
    """frames: [(данные, размер_после_распаковки)] одной папки cab -> bytes."""
    d = Decoder(window_bits)
    return b"".join(d.frame(data, size) for data, size in frames)
