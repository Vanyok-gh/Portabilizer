"""Автопроверка обновлений не чаще раза в сутки. Запуск: python tests/test_update_throttle.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P
n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1
check(P.update_check_due({}, now=2_000_000_000), "нет записи - проверяем")
check(not P.update_check_due({"last_update_check": 2_000_000_000}, now=2_000_000_000 + 3600), "час назад - не проверяем")
check(P.update_check_due({"last_update_check": 2_000_000_000}, now=2_000_000_000 + 86400), "сутки прошли - проверяем")
check(P.update_check_due({"last_update_check": 2_000_000_100}, now=2_000_000_000), "время в будущем (сбитые часы) - проверяем")
check(P.update_check_due({"last_update_check": "мусор"}, now=2_000_000_000), "битое значение - проверяем")
print(f"троттлинг проверки обновлений: {n} проверок пройдено")
