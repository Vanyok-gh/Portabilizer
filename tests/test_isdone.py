"""Распаковка репаков на ISDone: разбор настроек, правка компрессоров, проверка места.
Сам запуск ISDone, сборка C# и распаковка работают только в Windows и здесь не проверяются."""
import os
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pzp_isdone as D  # noqa: E402
import portabilizer_v8 as P  # noqa: E402

fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


# --- repack.cfg.ps1
r = D.parse_repack_cfg("$PasswordHex = '03050304'\n$Archives = @('data.bin','data1.bin','data2.bin')\n")
check(r["password_hex"] == "03050304" and r["archives"] == ["data.bin", "data1.bin", "data2.bin"],
      "cfg: пароль и список архивов")
check(r["cfg_name"] is None and not r["bad_password"], "cfg: без CfgName и без ошибок")
r = D.parse_repack_cfg("$PasswordHex = '-'\n$Archives = @('a.bin')\n$CfgName = 'arc,2.ini'")
check(r["password_hex"] == "-" and r["cfg_name"] == "arc,2.ini", "cfg: '-' значит без пароля, CfgName читается")
r = D.parse_repack_cfg("$PasswordHex = ''\n")
check(r["password_hex"] == "-", "cfg: пустой пароль = без пароля")
r = D.parse_repack_cfg("$PasswordHex = '0305z'\n")
check(r["password_hex"] is None and r["bad_password"], "cfg: неверный hex отмечен, пароль не угадывается")
r = D.parse_repack_cfg("$PasswordHex = '030'\n")
check(r["bad_password"], "cfg: нечётная длина hex - ошибка")
r = D.parse_repack_cfg("")
check(r["password_hex"] is None and r["archives"] is None and not r["bad_password"], "cfg: пустой текст")
r = D.parse_repack_cfg("$PasswordHex = '0a0b'")
check(r["password_hex"] == "0A0B", "cfg: hex приводится к верхнему регистру")

d = Path(tempfile.mkdtemp())
check(D.find_repack_cfg(d) is None, "find_repack_cfg: файла нет")
(d / D.CFG_FILE).write_text("$PasswordHex = '-'", encoding="ascii")
check(D.find_repack_cfg(d) == d / D.CFG_FILE, "find_repack_cfg: файл найден")
d2 = Path(tempfile.mkdtemp())
(d2 / "bin").mkdir()
(d2 / "bin" / D.CFG_FILE).write_text("$PasswordHex = '-'", encoding="ascii")
check(D.find_repack_cfg(d2) == d2 / "bin" / D.CFG_FILE, "find_repack_cfg: найден и в подпапке bin")
(d2 / D.CFG_FILE).write_text("$PasswordHex = '-'", encoding="ascii")
check(D.find_repack_cfg(d2) == d2 / D.CFG_FILE, "find_repack_cfg: рядом с установщиком важнее bin")

# --- архивы репака или части установщика
check(D.has_external_archives("C:/x/setup_game.exe", ["C:/x/data.bin", "C:/x/data1.bin"]), "bin: data*.bin - архивы репака")
check(not D.has_external_archives("C:/x/setup_game.exe", ["C:/x/setup_game-1.bin", "C:/x/setup_game-2.bin"]),
      "bin: части самого установщика не считаются")
check(D.has_external_archives("C:/x/setup.exe", ["C:/x/setup-1.bin", "C:/x/data.bin"]), "bin: смесь - репак")
check(not D.has_external_archives("C:/x/setup.exe", []), "bin: пусто - не репак")

# --- кодировки repack.cfg.ps1
txt = "$PasswordHex = '0A0B'\r\n$Archives = @('data.bin')\r\n"
cf = Path(tempfile.mkdtemp()) / "c.ps1"
for enc, name in (("utf-8", "utf-8"), ("utf-8-sig", "utf-8 с меткой"), ("utf-16", "utf-16 с меткой"),
                  ("utf-16-le", "utf-16 без метки"), ("cp1251", "ansi")):
    cf.write_bytes(txt.encode(enc))
    r = D.parse_repack_cfg(D.read_cfg_text(cf))
    check(r["password_hex"] == "0A0B" and r["archives"] == ["data.bin"], "кодировка cfg: " + name)

# --- какие arc*.ini пробовать
b = Path(tempfile.mkdtemp())
check(D.cfg_candidates(b) == [], "arc: ничего нет")
(b / "arc,1.ini").write_text("x")
(b / "arc,2.ini").write_text("x")
(b / "arc.ini").write_text("x")
check(D.cfg_candidates(b) == ["arc,1.ini", "arc,2.ini"], "arc: копия arc.ini пропускается, порядок 1, 2")
check(D.cfg_candidates(b, "arc,2.ini") == ["arc,2.ini", "arc,1.ini"], "arc: указанный в cfg идёт первым")
b2 = Path(tempfile.mkdtemp())
(b2 / "arc.ini").write_text("x")
check(D.cfg_candidates(b2) == ["arc.ini"], "arc: единственный arc.ini берётся")
b3 = Path(tempfile.mkdtemp())
for n in ("arc.ini", "arc$1.ini", "other.txt"):
    (b3 / n).write_text("x")
check(D.cfg_candidates(b3) == ["arc.ini", "arc$1.ini"], "arc: после innoextract первым идёт первый файл, потом переименованные")
check(D.cfg_candidates(Path(tempfile.mkdtemp()) / "нет") == [], "arc: нет папки - пусто")

# --- Global\ -> GlobalX
data = b"MZ..Global\\abc..\x00" + "Global\\wide".encode("utf-16-le") + b"..Global\\x"
new, n = D.patch_global_bytes(data)
check(n == 3 and len(new) == len(data), "Global: три замены, длина не изменилась")
check(b"Global\\" not in new and "Global\\".encode("utf-16-le") not in new, "Global: старых строк не осталось")
check(b"GlobalXabc" in new, "Global: ASCII заменён")
check("GlobalXwide".encode("utf-16-le") in new, "Global: UTF-16 заменён")
check(D.patch_global_bytes(new)[1] == 0, "Global: повторная правка ничего не меняет")

pd = Path(tempfile.mkdtemp())
(pd / "cls-lolz.dll").write_bytes(b"AAAA Global\\mem BBBB")
(pd / "cls-lolz_x64.exe").write_bytes(b"CCCC Global\\mem")
(pd / "ISDone.dll").write_bytes(b"keep Global\\ untouched")
(pd / "readme.txt").write_bytes(b"Global\\ in text")
(pd / "clean.dll").write_bytes(b"nothing here")
msgs = []
res = D.patch_global(pd, msgs.append)
check(res == {"cls-lolz.dll": 1, "cls-lolz_x64.exe": 1}, "patch_global: правятся только компрессоры")
check((pd / "ISDone.dll").read_bytes() == b"keep Global\\ untouched", "patch_global: ISDone.dll не тронут")
check((pd / "readme.txt").read_bytes() == b"Global\\ in text", "patch_global: не dll/exe не тронут")
check((pd / "_orig" / "cls-lolz.dll").read_bytes() == b"AAAA Global\\mem BBBB", "patch_global: оригинал сохранён")
check(not (pd / "_orig" / "clean.dll").exists(), "patch_global: ненужные оригиналы не копируются")
res2 = D.patch_global(pd, msgs.append)
check(res2 == res and (pd / "cls-lolz.dll").read_bytes() == b"AAAA GlobalXmem BBBB",
      "patch_global: повторный запуск безопасен")
check(bool(msgs), "patch_global: пишет в лог")

# --- cls.ini
ini = "[srep]\nMemory=75%-512m\n[lolz]\nMaxThreadsUsage=100%\nMaxMemoryUsage=75%\nldmfDeleteTmp=0\n"
t = D.tune_cls_ini(ini)
check("Memory=50%" in t and "MaxThreadsUsage=2" in t and "MaxMemoryUsage=1024m" in t and "ldmfDeleteTmp=1" in t,
      "cls.ini: память и потоки уменьшены")
check(D.tune_cls_ini(t) == t, "cls.ini: повторная правка ничего не меняет")
check(D.tune_cls_ini("[x]\na=1\n") == "[x]\na=1\n", "cls.ini: чужие строки не трогаются")

# --- LARGEADDRESSAWARE
pe = bytearray(0x200)
pe[0:2] = b"MZ"
struct.pack_into("<i", pe, 0x3C, 0x80)
pe[0x80:0x84] = b"PE\0\0"
struct.pack_into("<H", pe, 0x80 + 22, 0x0102)
out = D.set_large_address_aware(bytes(pe))
check(struct.unpack_from("<H", out, 0x80 + 22)[0] == 0x0122, "LAA: флаг добавлен, остальные сохранены")
check(len(out) == len(pe), "LAA: размер файла не изменился")
junk = b"not a pe file" * 10
check(D.set_large_address_aware(junk) == junk, "LAA: не PE не трогается")
check(D.set_large_address_aware(b"") == b"", "LAA: пустой файл не трогается")

# --- место
check(D.space_needed([1, 2, 3]) == 6 * D.SPACE_FACTOR and D.SPACE_FACTOR == 3, "место: 3x размера архивов")

# --- исходник распаковщика
src = D.UNPACKER_SOURCE
check("class UnpackerForm" in src and "ISArcExtract" in src and "MakeThunk" in src, "C#: исходник на месте")
check("\r" not in src and src.isascii(), "C#: только ASCII и LF")
check(src.count("{") == src.count("}"), "C#: скобки сбалансированы")

# --- Windows-часть
msgs = []
if os.name != "nt":
    check(D.extract_isdone("x/setup.exe", "x/out", msgs.append, None, None) is False and bool(msgs),
          "extract_isdone: не в Windows честно отказывает")
check(hasattr(P, "isdone_extract") and P.pzp_isdone is D, "основная программа подключает модуль")

# --- clear_dir
cd = Path(tempfile.mkdtemp())
(cd / "a").mkdir()
(cd / "a" / "f.txt").write_text("1")
(cd / "g.txt").write_text("2")
P.clear_dir(cd)
check(cd.is_dir() and not any(cd.iterdir()), "clear_dir: папка пуста, сама остаётся")

# --- прежнее определение типов не изменилось
ex = Path(tempfile.mkdtemp()) / "setup.exe"
ex.write_bytes(b"MZ" + b"\0" * 100 + b"Inno Setup Setup Data" + b"\0" * 100)
check(P.detect_type(ex) == "inno", "detect_type: Inno определяется как раньше")

if fails:
    print(f"\nПровалено: {len(fails)}")
    sys.exit(1)
print("\nВсе проверки пройдены")
