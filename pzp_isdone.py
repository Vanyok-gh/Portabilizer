"""Распаковка репаков Inno Setup с внешними .bin на движке ISDone (FreeArc) без прав администратора.

Установщик такого репака просит админа, поэтому его не запускают: движок распаковки (ISDone.dll, unarc.dll,
компрессоры) достаётся из setup.exe, а архивы распаковывает маленькая программа на C#, которую Windows
собирает встроенным csc.exe (ни SDK, ни админ не нужны).

Пароль архивов Portabilizer сам НЕ ищет: его (и список архивов) он берёт из файла repack.cfg.ps1 рядом
с установщиком. Без этого файла пробует без пароля и со всеми .bin рядом.

Модуль без интерфейса и без зависимостей от основной программы: запуск процессов и поиск утилит передаются
функциями. Чистые функции (разбор настроек, правка файлов, проверка места) проверяются тестами без Windows;
сама распаковка работает только в Windows и тестами не покрыта."""
import os
import re
import shutil
import struct
import subprocess
import time
from pathlib import Path

CFG_FILE = "repack.cfg.ps1"
ENGINE_FILES = ("ISDone.dll", "unarc.dll")        # без них распаковывать нечем
UNPACKER_EXE = "pzp_isdone_unpacker.exe"
QUICK_FAIL_SECONDS = 90                            # отказ быстрее: чаще всего не та конфигурация или пароль
SPACE_FACTOR = 3                                   # свободного места нужно ~3x размера архивов
# файлы самого движка не правим: в них нет общей памяти компрессоров
SKIP_PATCH = {"isdone.dll", "unarc.dll", "unarc.exe", "isskin.dll", "botva2.dll", "b2p.dll", "callbackctrl.dll"}
# процессы, которые остаются висеть, если распаковщик упал, и ломают следующий запуск
LEFTOVER_PROCS = ("cls-*", "xtool.exe", UNPACKER_EXE)
_GLOBAL_PAIRS = ((b"Global\\", b"GlobalX"),
                 ("Global\\".encode("utf-16-le"), "GlobalX".encode("utf-16-le")))


def parse_repack_cfg(text: str) -> dict:
    """Разбор repack.cfg.ps1: $PasswordHex = '...', $Archives = @('a','b'), необязательно $CfgName = '...'.
    password_hex: строка hex, "-" (без пароля) или None (не задан / записан неверно, тогда bad_password=True)."""
    res = {"password_hex": None, "archives": None, "cfg_name": None, "bad_password": False}
    m = re.search(r"\$PasswordHex\s*=\s*'([^']*)'", text)
    if m:
        v = m.group(1).replace(" ", "")
        if v in ("", "-"):
            res["password_hex"] = "-"
        elif len(v) % 2 == 0 and re.fullmatch(r"[0-9A-Fa-f]+", v):
            res["password_hex"] = v.upper()
        else:
            res["bad_password"] = True
    m = re.search(r"\$Archives\s*=\s*@\((.*?)\)", text, re.S)
    if m:
        res["archives"] = re.findall(r"'([^']+)'", m.group(1)) or None
    m = re.search(r"\$CfgName\s*=\s*'([^']+)'", text)
    if m:
        res["cfg_name"] = m.group(1)
    return res


def has_external_archives(setup, bins) -> bool:
    """Есть ли рядом .bin, которые НЕ части самого установщика Inno (<имя>-1.bin, <имя>-2.bin ...).
    Части установщика ставит сам Inno, а отдельные data.bin, data1.bin - это архивы репака."""
    stem = re.escape(Path(setup).stem)
    return any(not re.fullmatch(stem + r"-\d+\.bin", Path(b).name, re.I) for b in bins)


def read_cfg_text(path) -> str:
    """Текст repack.cfg.ps1. PowerShell 5.1 записывает файлы через > и Out-File в UTF-16, Блокнот в UTF-8:
    без разбора кодировки пароль в UTF-16 файле молча терялся бы."""
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    if len(raw) >= 4 and raw[1:2] == b"\x00" and raw[3:4] == b"\x00":     # UTF-16 LE без метки
        return raw.decode("utf-16-le", errors="ignore")
    return raw.decode("utf-8-sig", errors="ignore")


def find_repack_cfg(folder):
    """repack.cfg.ps1 рядом с установщиком или в его подпапке bin (так его кладёт набор скриптов)."""
    for p in (Path(folder) / CFG_FILE, Path(folder) / "bin" / CFG_FILE):
        if p.is_file():
            return p
    return None


def cfg_candidates(bin_dir, preferred=None) -> list:
    """Какие arc*.ini пробовать и в каком порядке: указанный в repack.cfg.ps1, затем arc,1.ini, затем
    arc.ini (innoextract оставляет первый файл с таким именем под этим именем, остальные переименовывает),
    затем остальные arc*.ini. Если innounp назвал дубли arc,1.ini / arc,2.ini, голый arc.ini (копия
    последнего запуска) пропускается."""
    bin_dir = Path(bin_dir)
    present = {f.name.lower(): f.name for f in bin_dir.iterdir()
               if f.is_file() and re.fullmatch(r"arc.*\.ini", f.name, re.I)} if bin_dir.is_dir() else {}
    has_numbered = any(n in present for n in ("arc,1.ini", "arc,2.ini"))
    order = ([preferred] if preferred else []) + ["arc,1.ini", "arc.ini"] + sorted(present.values(), key=str.lower)
    out, seen = [], set()
    for n in order:
        low = n.lower()
        if low in seen or low not in present:
            continue
        seen.add(low)
        if low == "arc.ini" and has_numbered and not (preferred and preferred.lower() == low):
            continue
        out.append(present[low])
    return out


def space_needed(sizes) -> int:
    return int(sum(sizes)) * SPACE_FACTOR


def patch_global_bytes(data: bytes):
    """'Global\\' -> 'GlobalX' (та же длина). Создавать объекты в пространстве Global\\ без админа нельзя,
    из-за этого lolz падает с 'Can't create read mapping!'. Возвращает (новые байты, число замен)."""
    buf = bytearray(data)
    n = 0
    for old, new in _GLOBAL_PAIRS:
        pos = buf.find(old)
        while pos >= 0:
            buf[pos:pos + len(old)] = new
            n += 1
            pos = buf.find(old, pos + len(new))
    return bytes(buf), n


def patch_global(bin_dir, log) -> dict:
    """Правит компрессоры в bin_dir. Оригиналы кладёт в bin_dir/_orig; повторный запуск берёт их оттуда,
    поэтому безопасен. Возвращает {имя файла: число замен}."""
    bin_dir = Path(bin_dir)
    orig_dir = bin_dir / "_orig"
    done = {}
    for f in sorted(bin_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() not in (".dll", ".exe") or f.name.lower() in SKIP_PATCH:
            continue
        orig = orig_dir / f.name
        new, n = patch_global_bytes((orig if orig.is_file() else f).read_bytes())
        if n:
            if not orig.is_file():
                orig_dir.mkdir(exist_ok=True)
                shutil.copy2(f, orig)
            f.write_bytes(new)
            done[f.name] = n
    if done:
        log("Компрессоры поправлены, чтобы работать без админа: "
            + ", ".join(f"{k} ({v})" for k, v in done.items()))
    return done


def tune_cls_ini(text: str) -> str:
    """Меньше памяти для srep и lolz (на 8 ГБ ОЗУ иначе раздувается файл подкачки и временные файлы)."""
    text = re.sub(r"Memory=75%-512m", "Memory=50%", text)
    text = re.sub(r"MaxThreadsUsage=\d+%", "MaxThreadsUsage=2", text)
    text = re.sub(r"MaxMemoryUsage=\d+%", "MaxMemoryUsage=1024m", text)
    text = text.replace("ldmfDeleteTmp=0", "ldmfDeleteTmp=1")
    return text


def set_large_address_aware(data: bytes) -> bytes:
    """Флаг LARGEADDRESSAWARE: 32-битный процесс получает 4 ГБ адресного пространства."""
    b = bytearray(data)
    if len(b) < 0x40:
        return bytes(b)
    pe = struct.unpack_from("<i", b, 0x3C)[0]
    if pe < 0 or pe + 24 > len(b) or bytes(b[pe:pe + 4]) != b"PE\0\0":
        return bytes(b)
    ch = struct.unpack_from("<H", b, pe + 22)[0] | 0x0020
    struct.pack_into("<H", b, pe + 22, ch)
    return bytes(b)


def find_csc():
    """csc.exe из .NET Framework 4, он входит в Windows."""
    win = os.environ.get("WINDIR") or r"C:\Windows"
    p = Path(win) / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe"
    return str(p) if p.is_file() else None


def kill_leftovers():
    if os.name != "nt":
        return
    for name in LEFTOVER_PROCS:
        try:
            subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True,
                           creationflags=0x08000000, timeout=20)
        except (OSError, subprocess.SubprocessError):
            pass


def extract_installer_files(setup: Path, bin_dir: Path, log, run_fn, find_tool) -> bool:
    """Достаёт из setup.exe движок распаковки и складывает все файлы плоско в bin_dir.
    Сначала innounp (так проверено), если его нет, innoextract (не проверено)."""
    tmp = bin_dir.parent / "_x"
    shutil.rmtree(tmp, ignore_errors=True)
    innounp = find_tool("innounp.exe")
    if innounp:
        log("Файлы движка достаю через innounp.")
        run_fn([innounp, "-x", "-m", "-y", f"-d{tmp}", str(setup)], log)
    else:
        ino = find_tool("innoextract.exe", "innoextract")
        if not ino:
            log("Нужен innounp.exe (положите рядом или в tools/) или innoextract.exe.")
            return False
        log("innounp.exe не найден, пробую innoextract: для движка ISDone это не проверено.")
        run_fn([ino, "-e", "-t", "--collisions", "rename", "-d", str(tmp), str(setup)], log)
    bin_dir.mkdir(parents=True, exist_ok=True)
    if tmp.is_dir():
        for p in tmp.rglob("*"):
            if p.is_file():
                shutil.copy2(p, bin_dir / p.name)
    shutil.rmtree(tmp, ignore_errors=True)
    missing = [n for n in ENGINE_FILES if not (bin_dir / n).is_file()]
    if missing:
        log("В установщике не нашлось файлов движка: " + ", ".join(missing)
            + ". Значит, это не репак на ISDone или файлы достались не полностью.")
        return False
    if not (bin_dir / "records.inf").is_file():
        log("Предупреждение: records.inf не найден, распаковка может не пойти.")
    return True


def build_unpacker(work: Path, bin_dir: Path, log, run_fn):
    """Собирает UNPACKER_SOURCE через csc.exe. Возвращает путь к exe или None."""
    csc = find_csc()
    if not csc:
        log("Не найден csc.exe (.NET Framework 4 входит в Windows): C# собрать нечем.")
        return None
    src_dir = work / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    src = src_dir / "Unpacker.cs"
    src.write_text(UNPACKER_SOURCE, encoding="ascii")
    exe = work / UNPACKER_EXE
    if exe.exists():
        exe.unlink()
    run_fn([csc, "/nologo", "/platform:x86", "/r:System.Windows.Forms.dll", f"/out:{exe}", str(src)], log)
    if not exe.is_file():
        log("Сборка распаковщика не удалась.")
        return None
    exe.write_bytes(set_large_address_aware(exe.read_bytes()))
    return str(exe)


def extract_isdone(setup, out, log, run_fn, find_tool, run_last=lambda: "") -> bool:
    """Распаковывает архивы репака рядом с setup в папку out. run_last() возвращает хвост вывода
    последнего запуска (в основной программе это run.last)."""
    if os.name != "nt":
        log("Распаковка на ISDone работает только в Windows.")
        return False
    setup, out = Path(setup), Path(out)
    folder = setup.parent
    cfg_file = find_repack_cfg(folder)
    cfg = {"password_hex": None, "archives": None, "cfg_name": None, "bad_password": False}
    if cfg_file:
        log(f"Настройки репака: {cfg_file.name}")
        cfg = parse_repack_cfg(read_cfg_text(cfg_file))
        if cfg["bad_password"]:
            log("В repack.cfg.ps1 PasswordHex записан неверно (нужны пары hex-символов, например 03050304).")
            return False
    else:
        log(f"Файла {CFG_FILE} рядом с установщиком нет: пробую без пароля и со всеми .bin "
            f"(это предположение). Если архивы под паролем, положите рядом {CFG_FILE} "
            "с $PasswordHex = '...' (hex) и $Archives = @('data.bin', ...).")
    password_hex = cfg["password_hex"] or "-"
    archives = cfg["archives"] or sorted(p.name for p in folder.glob("*.bin"))
    if not archives:
        log("Рядом с установщиком нет .bin файлов: распаковывать нечего.")
        return False
    absent = [a for a in archives if not (folder / a).is_file()]
    if absent:
        log("Не найдены архивы: " + ", ".join(absent))
        return False
    sizes = [(folder / a).stat().st_size for a in archives]
    probe = out
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        free = shutil.disk_usage(probe).free
    except OSError:
        free = None
    need = space_needed(sizes)
    if free is not None and free < need:
        log(f"Мало места: на диске {free / 2**30:.1f} ГБ, а для распаковки нужно около {need / 2**30:.1f} ГБ "
            f"({SPACE_FACTOR} размера архивов). FreeArc не умеет продолжать с середины, "
            "поэтому лучше освободить место или выбрать другой диск.")
        return False
    for p in (folder, out):
        if not str(p).isascii():
            log(f"Предупреждение: в пути {p} не латинские символы. ISDone работает с ANSI-путями, "
                "с кириллицей и другими символами может не распаковать.")
            break

    work = out.parent / "ISDone_work"
    bin_dir = work / "bin"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    ok = False
    try:
        kill_leftovers()
        if not extract_installer_files(setup, bin_dir, log, run_fn, find_tool):
            return False
        patch_global(bin_dir, log)
        ini = bin_dir / "cls.ini"
        if ini.is_file():
            old = ini.read_text(encoding="latin-1")
            new = tune_cls_ini(old)
            if new != old:
                ini.write_text(new, encoding="latin-1")
                log("Память srep/lolz уменьшена (cls.ini), чтобы не раздувало файл подкачки.")
        unpacker = build_unpacker(work, bin_dir, log, run_fn)
        if not unpacker:
            return False
        cands = cfg_candidates(bin_dir, cfg["cfg_name"])
        if not cands:
            log("В установщике нет конфигурации архивов (arc.ini / arc,1.ini).")
            return False
        out.mkdir(parents=True, exist_ok=True)
        for n, name in enumerate(cands):
            log(f"Распаковываю {len(archives)} арх., конфигурация {name} "
                f"({sum(sizes) / 2**30:.1f} ГБ архивов, это может занять часы)...")
            cmd = [unpacker, str(folder), str(bin_dir), str(out), password_hex, name] + archives
            t0 = time.monotonic()
            ok = run_fn(cmd, log)
            took = time.monotonic() - t0
            kill_leftovers()
            if ok:
                break
            last = run_last().lower()
            if "wrong password" in last or "-13" in last:
                log(f"Пароль не подошёл. Проверьте PasswordHex в {CFG_FILE}.")
                break
            if took < QUICK_FAIL_SECONDS and n + 1 < len(cands):
                log(f"Отказ за {took:.0f} с: так бывает при не той конфигурации архивов. "
                    "Пробую следующую (это эвристика, текст ошибки ISDone программа не видит).")
                continue
            if took < QUICK_FAIL_SECONDS:
                log(f"Отказ за {took:.0f} с, конфигурации кончились. Чаще всего так бывает, когда архивы "
                    "под паролем, а его не дали: проверьте " + CFG_FILE
                    + " (в нём $PasswordHex в hex) рядом с установщиком или в папке bin.")
            break
        if not ok:
            log("Распаковка не удалась. Рабочие файлы оставлены в " + str(work))
        return ok
    finally:
        kill_leftovers()
        if ok:
            shutil.rmtree(work, ignore_errors=True)


# Исходник распаковщика (x86, собирается csc.exe). Копия проверенного набора скриптов.
UNPACKER_SOURCE = r'''// ISDone-based unpacker for Inno Setup repacks (xatab style), no admin rights needed.
// Build:   x86 only (ISDone.dll is 32-bit), then set LARGEADDRESSAWARE (see 05_build_unpacker.ps1)
// Usage:   Unpacker.exe <repackDir> <binDir> <outputDir> <passwordHex|-> <cfgName> <archive1> [archive2 ...]
//   repackDir  folder with data*.bin
//   binDir     folder with ISDone.dll, unarc.dll, arc*.ini, cls*.*, xtool.exe ... (extracted by innounp)
//   outputDir  where the game goes (must be writable by the user)
//   passwordHex archive password as hex bytes (from 02_find_password.ps1), "-" for no password
//   cfgName    which arc*.ini to use (copied to binDir\arc.ini)
// Exit code: 0 = all OK, 1 = init failed, 2 = extract error, 3 = bad args

using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

class UnpackerForm : Form
{
    // Our managed callback, stdcall, 6 args
    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    delegate uint ProgressCb(int overall, int current, IntPtr curFile, IntPtr t1, IntPtr t2, IntPtr t3);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    static extern bool SetDllDirectory(string p);

    [DllImport("kernel32.dll")]
    static extern IntPtr VirtualAlloc(IntPtr addr, UIntPtr size, uint type, uint protect);

    // ISDoneInit: 9 dwords (ret 0x24). Last two = Delphi method pointer (Code, Data).
    [DllImport("ISDone.dll", CallingConvention = CallingConvention.StdCall)]
    [return: MarshalAs(UnmanagedType.U1)]
    static extern bool ISDoneInit(IntPtr recordFile, uint timeType, uint comp1, uint comp2, uint comp3,
                                  IntPtr winHandle, int neededMem, IntPtr cbCode, IntPtr cbData);

    [DllImport("ISDone.dll", CallingConvention = CallingConvention.StdCall)]
    static extern void ISDoneStop();

    // ISArcExtract: 11 dwords (ret 0x2c), double takes 2.
    [DllImport("ISDone.dll", CallingConvention = CallingConvention.StdCall)]
    [return: MarshalAs(UnmanagedType.U1)]
    static extern bool ISArcExtract(uint curComponent, double pctOfTotal,
        IntPtr inName, IntPtr outPath, IntPtr extractedPath,
        [MarshalAs(UnmanagedType.U1)] bool deleteInFile,
        IntPtr password, IntPtr cfgFile, IntPtr workPath,
        [MarshalAs(UnmanagedType.U1)] bool extractPCF);

    // Delphi 7 AnsiString literal: [RefCount=-1][Length][bytes][0], pointer to bytes
    static IntPtr DBytes(byte[] b, out IntPtr raw)
    {
        if (b == null || b.Length == 0) { raw = IntPtr.Zero; return IntPtr.Zero; }
        raw = Marshal.AllocHGlobal(8 + b.Length + 1);
        Marshal.WriteInt32(raw, 0, -1);
        Marshal.WriteInt32(raw, 4, b.Length);
        Marshal.Copy(b, 0, IntPtr.Add(raw, 8), b.Length);
        Marshal.WriteByte(raw, 8 + b.Length, 0);
        return IntPtr.Add(raw, 8);
    }

    static IntPtr DStr(string s, out IntPtr raw)
    {
        return DBytes(string.IsNullOrEmpty(s) ? null : Encoding.GetEncoding(1251).GetBytes(s), out raw);
    }

    static void Free(IntPtr raw) { if (raw != IntPtr.Zero) Marshal.FreeHGlobal(raw); }

    static byte[] FromHex(string hex)
    {
        if (string.IsNullOrEmpty(hex) || hex == "-") return null;
        hex = hex.Replace(" ", "");
        byte[] r = new byte[hex.Length / 2];
        for (int i = 0; i < r.Length; i++) r[i] = Convert.ToByte(hex.Substring(i * 2, 2), 16);
        return r;
    }

    // ISDone calls the callback as a Delphi *method* with register convention:
    //   EAX=Self, EDX=a1, ECX=a2, stack (pushed left-to-right): a3,a4,a5,a6 ; callee pops 16.
    // This thunk rebuilds a normal stdcall call target(a1..a6).
    static IntPtr MakeThunk(IntPtr target)
    {
        byte[] c = {
            0xFF,0x74,0x24,0x04,   // push [esp+4]   a6
            0xFF,0x74,0x24,0x0C,   // push [esp+12]  a5
            0xFF,0x74,0x24,0x14,   // push [esp+20]  a4
            0xFF,0x74,0x24,0x1C,   // push [esp+28]  a3
            0x51,                  // push ecx       a2
            0x52,                  // push edx       a1
            0xB8,0,0,0,0,          // mov eax, target
            0xFF,0xD0,             // call eax       (stdcall, pops 24)
            0xC2,0x10,0x00         // ret 16
        };
        Array.Copy(BitConverter.GetBytes(target.ToInt32()), 0, c, 19, 4);
        IntPtr mem = VirtualAlloc(IntPtr.Zero, (UIntPtr)64, 0x3000, 0x40); // MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE
        Marshal.Copy(c, 0, mem, c.Length);
        return mem;
    }

    static string[] A;
    static int exitCode = 0;
    static ProgressCb cb;
    int lastPct = -1;

    uint OnProgress(int overall, int current, IntPtr curFile, IntPtr t1, IntPtr t2, IntPtr t3)
    {
        if (overall != lastPct)
        {
            lastPct = overall;
            Console.Write("\rTotal: " + (overall / 10.0).ToString("F1") + "%   Archive: " + (current / 10.0).ToString("F1") + "%        ");
        }
        Application.DoEvents();
        return 0; // 0 = continue
    }

    protected override void OnShown(EventArgs e)
    {
        base.OnShown(e);
        Application.DoEvents();

        string repackDir = A[0], binDir = A[1], outputDir = A[2];
        byte[] pwd = FromHex(A[3]);
        string cfgName = A[4];

        Directory.CreateDirectory(outputDir);
        Directory.SetCurrentDirectory(binDir);
        SetDllDirectory(binDir);

        string arcIni = Path.Combine(binDir, "arc.ini");
        if (!string.Equals(Path.Combine(binDir, cfgName), arcIni, StringComparison.OrdinalIgnoreCase))
            File.Copy(Path.Combine(binDir, cfgName), arcIni, true);
        Console.WriteLine("Config: " + cfgName);

        cb = new ProgressCb(OnProgress);
        IntPtr thunk = MakeThunk(Marshal.GetFunctionPointerForDelegate(cb));

        IntPtr rRec;
        IntPtr pRec = DStr(Path.Combine(binDir, "records.inf"), out rRec);
        try
        {
            bool init = ISDoneInit(pRec, 0x1111, 0, 0, 0, this.Handle, 0, thunk, IntPtr.Zero);
            Console.WriteLine("ISDoneInit: " + init);
            if (!init) { exitCode = 1; return; }

            for (int i = 5; i < A.Length; i++)
            {
                string arc = A[i];
                string full = Path.IsPathRooted(arc) ? arc : Path.Combine(repackDir, arc);
                if (!File.Exists(full)) { Console.WriteLine("Missing " + full); exitCode = 2; break; }

                IntPtr rIn, rOut, rPwd, rCfg, rWork;
                IntPtr pIn = DStr(full, out rIn);
                IntPtr pOut = DStr(outputDir.TrimEnd('\\') + "\\", out rOut);
                IntPtr pPwd = DBytes(pwd, out rPwd);
                IntPtr pCfg = DStr(arcIni, out rCfg);
                IntPtr pWork = DStr(outputDir.TrimEnd('\\') + "\\", out rWork);
                try
                {
                    Console.WriteLine("\nExtracting " + arc + " ...");
                    bool ok = ISArcExtract(0, 0.0, pIn, pOut, IntPtr.Zero, false, pPwd, pCfg, pWork, false);
                    Console.WriteLine("\n" + arc + ": " + (ok ? "OK" : "ERROR"));
                    if (!ok) { exitCode = 2; break; }
                }
                finally { Free(rIn); Free(rOut); Free(rPwd); Free(rCfg); Free(rWork); }
            }
        }
        finally
        {
            ISDoneStop();
            Free(rRec);
            GC.KeepAlive(cb);
            Application.Exit();
        }
    }

    [STAThread]
    static int Main(string[] args)
    {
        if (args.Length < 6)
        {
            Console.WriteLine("Usage: Unpacker.exe <repackDir> <binDir> <outputDir> <passwordHex|-> <cfgName> <archive1> [archive2 ...]");
            return 3;
        }
        A = args;
        Application.Run(new UnpackerForm { Width = 300, Height = 100, Text = "Unpacking..." });
        return exitCode;
    }
}
'''
