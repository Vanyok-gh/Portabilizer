"""InstallShield: подпапка группы Common<Имя> выводится по пустой папке кабинета (group_subdir).
Кабинет собирается тестовым построителем из tests/test_isc.py. Запуск: python tests/test_isc_subdirs.py"""
import ast, hashlib, struct, sys, tempfile, zlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import pzp_isc as I

# функции pack/build берём из test_isc.py, не выполняя его проверки
tree = ast.parse((HERE / "test_isc.py").read_text(encoding="utf-8"))
ns = {"hashlib": hashlib, "struct": struct, "zlib": zlib, "Path": Path, "I": I}
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in ("pack", "build"):
        exec(compile(ast.Module([node], []), "test_isc", "exec"), ns)
build = ns["build"]

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def f(name, d, data=b"x"):
    return dict(name=name, dir=d, data=data, vol=1, kind="z")

FILES = [f("quick.bundle", ""), f("hud.xml", ""), f("snd.pak", ""), f("menu.xml", ""), f("a.dds", "textures"),
         f("data.bin", ""), f("loose.txt", "")]
GROUPS = [("CommonBundles", 0, 0), ("CommonSettings", 1, 1), ("CommonSounds", 2, 2), ("CommonMenu", 3, 3),
          ("CommonTextures", 4, 4), ("CommonData", 5, 5), ("Common", 6, 6)]
# папки: sounds и menu пустые (кандидаты), textures не пустая, bundles/settings известны, data нет вообще
DIRS = ["", "bundles", "settings", "Sounds", "menu", "textures"]

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    build(t, DIRS, FILES, GROUPS)
    (t / "setup.exe").write_bytes(b"MZ" + b"\0" * 100)
    cab = I.open_cabinet(t / "setup.exe")
    check(cab.dirs == DIRS, f"список папок сохранён: {cab.dirs}")
    sub = lambda g: I.group_subdir(cab, g)       # noqa: E731
    check(sub("CommonBundles") == "bundles" and sub("CommonSettings") == "settings", "известные группы")
    check(sub("CommonSounds") == "Sounds", f"пустая папка Sounds -> группа CommonSounds: {sub('CommonSounds')!r}")
    check(sub("CommonMenu") == "menu", "пустая папка menu -> CommonMenu")
    check(sub("CommonTextures") == "", "папка textures не пустая: подпапку не выводим")
    check(sub("CommonData") == "", "папки data нет: корень")
    check(sub("Common") == "" and sub("Arch") == "", "группа без суффикса и без префикса Common: корень")
    check(set(cab.inferred) == {"CommonSounds", "CommonMenu"}, f"выведенные помечены: {cab.inferred}")
    files, _, _ = I.select_files(cab, "en")
    rels = sorted(r.replace("\\", "/") for _, r in files)
    check("Sounds/snd.pak" in rels and "menu/menu.xml" in rels and "bundles/quick.bundle" in rels, f"пути: {rels}")
    check("data.bin" in rels and "textures/a.dds" in rels, "остальные на месте")
    logs = []
    count, size, errors = I.extract_game(cab, t / "App", "en", logs.append)
    check(count == len(FILES) and not errors, f"извлечено {count}, ошибки {errors}")
    check((t / "App" / "Sounds" / "snd.pak").is_file(), "файл лежит в выведенной подпапке")
    text = "\n".join(logs)
    check("по структуре кабинета (предположение" in text and "CommonSounds" in text, "в журнале сказано, что это предположение")

print(f"OK: {n} проверок")
