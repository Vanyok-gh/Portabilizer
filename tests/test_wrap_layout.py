"""Перенос настроек на новую строку в узком окне (wrap_positions). Запуск: python tests/test_wrap_layout.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

W = [250, 300, 240, 330]          # режим, запуск, скриншоты, оптимизация во весь экран
check(P.wrap_positions([], 800) == [], "пусто")
check(P.wrap_positions(W, 10 ** 6) == [(0, 0), (0, 1), (0, 2), (0, 3)], "широкое окно: всё в одну строку")
check(P.wrap_positions(W, 900) == [(0, 0), (0, 1), (0, 2), (1, 0)], f"900 px: {P.wrap_positions(W, 900)}")
check(P.wrap_positions(W, 600) == [(0, 0), (0, 1), (1, 0), (1, 1)], "600 px: две строки по два")
check(P.wrap_positions(W, 300) == [(0, 0), (1, 0), (2, 0), (3, 0)], "узкое окно: по одному в строке")
check(P.wrap_positions([500, 500], 100) == [(0, 0), (1, 0)], "виджет шире окна не теряется и не зацикливается")
# ширина с зазором: 250+8 + 300+8 = 566 помещается в 566, но не в 565
check(P.wrap_positions([250, 300], 566) == [(0, 0), (0, 1)] and P.wrap_positions([250, 300], 565) == [(0, 0), (1, 0)],
      "граница: ровно по ширине помещается, на пиксель меньше переносится")
# порядок виджетов сохраняется, строки не убывают
pos = P.wrap_positions([120] * 20, 500)
check([p[0] for p in pos] == sorted(p[0] for p in pos), "строки идут по порядку")
check(max(c for _, c in pos) + 1 == 3, "в строке по три виджета по 120+8 в 500")

print(f"OK: {n} проверок")
