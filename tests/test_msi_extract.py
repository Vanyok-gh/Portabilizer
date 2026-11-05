"""Распаковка MSI: порядок вызовов msiexec, повтор без InstallScript, уборка временных файлов.
Запуск: python tests/test_msi_extract.py (сам msiexec и PowerShell проверяются только в Windows)."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def scenario(first_ok, second_ok):
    calls = []
    def fake_run(cmd, log, ok_codes=(0,), job=None, track_progress=False):
        calls.append(cmd)
        s = cmd if isinstance(cmd, str) else " ".join(map(str, cmd))
        fake_run.rc = 0
        if s.startswith("msiexec"):
            msi_n = sum(1 for c in calls if isinstance(c, str))
            good = first_ok if msi_n == 1 else second_ok
            fake_run.rc = 0 if good else 1603
            if good:
                (out / "TRAOD.exe").write_bytes(b"x")
            return good
        return True
    fake_run.rc = 0
    old = P.run; P.run = fake_run
    try:
        res = P.msi_admin_extract(src, out, lambda *_: None)
    finally:
        P.run = old
    return res, calls

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    src = d / "Lara Croft Tomb Raider.msi"; src.write_bytes(b"msi")
    out = d / "res" / "App"; out.mkdir(parents=True)

    res, calls = scenario(True, False)
    check(res and len(calls) == 1, "удача с первого раза: один вызов msiexec")
    check(calls[0].startswith('msiexec /a "') and f'TARGETDIR="{out}"' in calls[0] and "/qn" in calls[0],
          "TARGETDIR в кавычках вокруг значения")
    check("/l*v" in calls[0], "подробный лог msiexec")

    (out / "TRAOD.exe").unlink()
    res, calls = scenario(False, True)
    check(res and len(calls) == 3, "первая попытка не удалась: чистка + msiexec на копии")
    check(isinstance(calls[1], list) and calls[1][0] == "powershell", "чистка копии идёт через PowerShell")
    check("_pz_tmp.msi" in calls[2], "повтор на временной копии")
    check(not (d / "Lara Croft Tomb Raider_pz_tmp.msi").exists(), "временная копия удалена")
    check(not (d / "res" / "_msi_strip.ps1").exists(), "временный ps1 удалён")
    check(src.read_bytes() == b"msi", "оригинал msi не тронут")

    (out / "TRAOD.exe").unlink()
    res, calls = scenario(False, False)
    check(not res, "обе попытки неудачны: False")

import glob
real = glob.glob("/mnt/user-data/attachments/*/*Lara_Croft*.msi")
if real:
    import pzp_msi
    with tempfile.TemporaryDirectory() as d2:
        d2 = Path(d2); (d2 / "x.msi").write_bytes(Path(real[0]).read_bytes())
        m1 = pzp_msi.missing_source_files(d2 / "x.msi")
        check(len(m1) > 100 and any(p.endswith("PARIS6.GMX.CLZ") for _, p in m1), "без папок: все несжатые файлы отсутствуют")
        (d2 / "Data" / "Maps").mkdir(parents=True); (d2 / "Data" / "Maps" / "PARIS6.GMX.CLZ").write_bytes(b"1")
        m2 = pzp_msi.missing_source_files(d2 / "x.msi")
        check(len(m2) == len(m1) - 1 and not any(p.endswith("PARIS6.GMX.CLZ") for _, p in m2), "найденный файл больше не отсутствует")
        check(not any(k == "TRAOD.exe1" for k, _ in m1), "файлы внутри cab не считаются отсутствующими")
check("KeysFile" in P.MSI_STRIP_PS and "DELETE FROM File WHERE File=" in P.MSI_STRIP_PS, "скрипт убирает строки отсутствующих файлов")
check("IS*" in P.MSI_STRIP_PS and "AdminExecuteSequence" in P.MSI_STRIP_PS, "скрипт чистит IS-действия")
check("Component_='DirectX9'" in P.MSI_STRIP_PS, "файлы DirectX9 убираются из черновика")
check("`" not in P.MSI_STRIP_PS, "в PowerShell-тексте нет обратных кавычек (экранирование)")
print(f"MSI: {n} проверок пройдено")
