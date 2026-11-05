#!/usr/bin/env python3
"""
Portabilizer v8.9 - превращает установщик, пакет или архив в портативную папку.

Вход: exe-установщики (Inno Setup, NSIS, WiX), MSI, MSIX/APPX/бандлы,
архивы (rar, zip, 7z, tar, gz, cab, iso, многотомные .part1.rar), обычные exe.

Что делает:
  1. Определяет тип файла.
  2. Распаковывает БЕЗ установки в систему (7-Zip / innoextract / msiexec)
     или, если нужна установка (репак с внешними .bin), тихо ставит прямо в папку App.
  3. Находит главный exe (для MSIX - по AppxManifest.xml; можно указать вручную).
  4. Создаёт Launch.bat, который перенаправляет APPDATA, LOCALAPPDATA,
     USERPROFILE и TEMP в папку Data рядом с программой.
  5. Кладёт Create_Shortcut.bat и предлагает ярлык на рабочем столе с иконкой программы.
  Отдельно: вкладка «Образ ISO» собирает образ диска из папки (для игр, которым нужен диск с меткой в приводе).

Режимы:
  auto      - сначала распаковка; если нужна установка (репак) - пробует её,
              а распакованное сохраняет в папке Extracted (ничего не удаляется).
  extract   - только распаковка, без установки.
  install   - только тихая установка в App (Inno/NSIS; сначала без админа, затем UAC).
  launcher  - папка *_portable уже есть: только создать Launch.bat.

Что нового в v8:
  - единое приложение: окно и командная строка в одном Portabilizer.exe (сборка - build.bat);
    запуск без аргументов открывает окно, с аргументами работает как консольная утилита;
  - иконка с пером в окне и панели задач; у версии (R) она красная;
  - вкладка «Версии»: обычный Portabilizer и Portabilizer (R) - радикальный. В режиме R исходный
    файл (установщик, пакет или архив, все тома) и временные копии УДАЛЯЮТСЯ после успешной
    сборки, итог занимает меньше места. Перед каждым запуском - предупреждение. Удаление идёт
    только если всё проверено: Launch.bat создан, распаковщик не сообщал о предупреждениях,
    размер сходится; при ошибке и отмене исходник остаётся. Места на время работы нужно
    столько же, как в обычной версии. Командная строка: --radical --yes;
  - игры на Unreal Engine: Launch.bat запускает ...-Shipping.exe напрямую (Launch_stub.bat -
    запуск через корневой exe); если в системе нет xinput1_3.dll (DirectX June 2010), создаётся
    DX_fix.bat: он кладёт нужные библиотеки рядом с игрой без прав администратора;
  - заметки о конвертации в «Истории» (что пришлось доделать);
  - исправление: .bat/.ps1, которые создаёт программа, больше не получают лишний символ
    возврата каретки при записи в Windows (в v7.3 так могло быть у Install_dotnet.*).

Что нового в v8.9:
  - режим (R): обычный exe больше не копируется, а ПЕРЕНОСИТСЯ в App (на одном диске это
    мгновенно и без дополнительного места). Архивы и установщики по-прежнему сначала
    распаковываются, поэтому на время работы нужно место под распакованное;
  - пиксельные иконки пера (обычная версия - синее, R - красное) при теме «Классическая
    (системная)»; в остальных темах - гладкие.

Что нового в v7.3:
  - умнее выбор главного exe. Игры на Unreal Engine распознаются: запускается корневой exe
    (например, VotV.exe), а не exe из Binaries и не патчер. Патчеры, обновлялки и вспомогательные
    программы (patch, updater, ffmpeg, CEF SubProcess...) идут в конец очереди;
  - если подходящих программ несколько и явного победителя нет, окно предложит выбрать
    (в командной строке берётся первая, остальные перечисляются в логе);
  - .NET: по файлу *.runtimeconfig.json рядом с главным exe программа понимает, какой .NET
    нужен. Если его нет на компьютере, в папке появятся Install_dotnet.bat и Install_dotnet.ps1:
    они скачивают нужный рантайм в папку dotnet внутри портативной копии, права администратора
    не нужны. Launch.bat сам подхватывает папку dotnet, если она есть.

Что нового в v7.2:
  - когда места мало, задача встаёт на паузу и появляется окно с выбором: «Продолжить»,
    «Остановить: почищу диск» или «Отменить загрузку». В окне видно, сколько ещё осталось
    записать и хватит ли свободного места, чтобы дойти до конца. «Продолжить» после этого
    не пугается порога 100 МБ и останавливает задачу снова, только если свободно меньше 20 МБ.

Что нового в v7.1:
  - порог защиты диска теперь 100 МБ (было 1,5 ГБ). Чтобы диск не успел заполниться между
    проверками, к порогу добавляется запас на скорость записи: чем быстрее убывает место,
    тем раньше включается пауза;
  - если главный exe не найден, в лог выводится список найденных exe и причина, по которой
    каждый отсеян; консольные exe теперь берутся запасным вариантом, если больше ничего нет.

Что нового в v7:
  - вкладки: «Конвертер», «История», «Диагностика»;
  - управление задачей: Пауза / Продолжить / Прервать (процесс реально замораживается
    и размораживается, ничего не теряется);
  - защита от переполнения диска: перед стартом оценивается нужное место,
    а во время работы при остатке меньше 100 МБ (с запасом на скорость записи) задача сама встаёт на паузу;
  - прогресс распаковки в процентах и оставшееся время (для 7z);
  - история всех конвертаций (portabilizer_history.json): двойной щелчок открывает
    результат в проводнике, есть «Запустить», «Повторить»;
  - удаление: портативной копии (только папок, созданных Portabilizer) и исходного
    файла (rar, установщик) - всегда с подтверждением;
  - диагностика в стиле игровой панели: CPU, RAM, GPU, скорость диска, свободное место;
  - панель рекомендаций: подсказки при нехватке места и типовых ошибках.

Про паузу и «продолжить»: пауза замораживает 7z/установщик, их можно продолжить с того же
места. Если задачу ПРЕРВАТЬ, продолжить с места остановки нельзя (7z так не умеет):
во вкладке «История» есть «Повторить» - оно начнёт заново.

Зависимости: Python 3.9+, tkinter. Для паузы, нагрузки CPU/RAM и диагностики нужен
psutil:  pip install psutil

Сборка единого приложения: положите рядом папку assets (portabilizer.ico, portabilizer_R.ico),
7z.exe + 7z.dll (и по желанию innoextract.exe) и запустите build.bat. Получится
dist/Portabilizer.exe: двойной щелчок открывает окно, а с аргументами он работает как
консольная утилита. Ярлык «Portabilizer (R)» с красной иконкой создаётся там же.
Положите рядом 7z.exe + 7z.dll (и по желанию innoextract.exe).

Командная строка:
  portabilizer_v8.py файл [папка_назначения] [--mode=auto|extract|install|launcher] [--run=auto|noadmin|admin] [--dx=install|skip|cancel]
                     [--exe=Game.exe] [--force]
  --force  начать, даже если места на диске, скорее всего, не хватит.
"""
import codecs
import collections
import datetime
import json
import os
import platform
import re
import shutil
import stat
import struct
import subprocess
import sys
import threading
import time
import uuid
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

from pzp_i18n import LANGS, detect_lang, get_lang, lang_name, set_lang, tr, trx
from pzp_iso import IsoError, build_iso

try:
    import psutil
except ImportError:           # без psutil работают конвертация и диски, но нет паузы через psutil и нагрузки
    psutil = None

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
MODES = ("auto", "extract", "install", "launcher")
MSIX_EXT = (".msix", ".appx", ".msixbundle", ".appxbundle")
ARCHIVE_EXT = (".rar", ".zip", ".7z", ".tar", ".gz", ".tgz", ".xz", ".bz2",
               ".cab", ".iso")
ARCHIVE_MAGIC = (b"Rar!\x1a\x07", b"7z\xbc\xaf\x27\x1c", b"PK\x03\x04")

GB = 1024 ** 3
LOW_SPACE = 100 * 1024 ** 2     # меньше свободного места (плюс запас на скорость записи) - пауза
WATCH_INTERVAL = 0.5            # как часто проверять свободное место, сек
HARD_FLOOR = 20 * 1024 ** 2      # после «Продолжить» пауза включится снова только ниже этого
DISK_WARN = 3 * GB              # ниже этого диск подсвечивается в диагностике
MARKER = ".portabilizer.json"   # метка в папках, которые создал Portabilizer
HISTORY_FILE = "portabilizer_history.json"
# иконки (PNG в base64) для окна и панели задач: перо; у версии (R) красное
ICONS = {'blue32': 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAFAklEQVR42sWXaWxVRRTH/zNz73u3fd1b6AJIASHhFYqhARVSWlFaSYgV4bYkRDE1AYLRxN3gcntZ9AMmGhESFzSGiPY9QIEYlkJLIQVUEGpooQs0qEVa2bqQt92Z44f2c1u6eZL5Npn5nf9Z5gwwvMZ61+ibZVkc/5f5fD4BACbgWm1Oju8VYVSUYETEAOCZxTnzzTVv1S55/rXTBPARV8SywMF6nFzxXKm9ZVelLFz7CRW8W0UrVpqlAJCXZ2kjdTsHYxgPJK15/f1DX9e006cHr6ipC1dHFm/tVEvWfXTVmggDPer0GQo+KNnLyiiRKH7pe1sq5pW8XRiXNiZyrnIvk+4UjXGukPbIpEsPL10GxigvzxLDCcAsyxKMMSx/5Z3yuU+/NFtKRAKdjn7uxCFEp0wGhTohPRMplDhrJQCMfTGLhg3Asixh27az4tlVm+YUrSuUxCKaS+gtdWfRWFcLjXNIJ8gkCSaNVK8FuPzFJbKvMAwYwDRNYdsbnMIncgsferJ0fXRihhO616W5DReO+bZD6QmIH+/t3U1gAyzDgQJwr9dH09IpJXvRqm8mzFhAga673PDEsustLThzZDfSsxbCHZcK5TjEGSMW7mi1gTBIMQA0JACfz8dsm6lHi17elJVfkh4KBSURcSPahao9nyMUDCB1+mPgQgMYJ011Ma27pQoA8srKhpaElmXx4uISOSd70rRJOQWlwh2jZDgoNJeBuzfvoPqnHYgaOx1xE2ZCRYIELZqj7degcb1yBwDkA2qoIeAAwTt/ydrMmQv0SDigCGBRniicrfwRHbdvYvzsIrg8CZDg0qBOrt84uW3Xsaarps8nbNvuE6C/TsU2bNjoADBSH8xZrkXFItjdyTkXiIQjOFr+GZgwMMb7OEg5iutRnP195FZMwxcfgoj5GVNDSkLTNDmRwuJFufPSJs+aIB1HESluRHvQeOE0Wi6dR/LUXMSkToEjiYxIG9fbjn+w8zfc6o099QfQpwJer5cBwNipOQVJ6VOgpKOIiGs6xy9H/ACAtJmF4LpbQSrOWioaY0+Vb7cs4rbN5JDLMCurjAAgLil9hm54IGWECd2F7o5uXDhxAFyPRkJmDiQJct+7wowbVeu/vcaC9fXFbCDeDyAEPYcIlxEbURxKKriNKPzZ9Af+vX4NCZlzYCQ/IDU4grdW1vj3HtxjmuXC7/fLgTa4PgH8/p5uJiOhzow4QHCC0Dkafj8JAEieMhciOgXi5lkY7RVvEhgA/309Ln0C1NWVMQAIdrQ1j48Jk0vXSUmgubYG4DrSc5ZLl+wQWuvR78r3nT51v973C1BfX08A8FdjbcXPpxqYZC4eDgTQ2lQLT9p0ih03g6Fl/21Pyw9vwLK431tHwMiMXO5XN29r/v4iqa0VrdKlCxo3f7Wz7OMGWlpUuKYnX3xiMBf01wmprKeeQ83nD2++d+sfFg4GVTgiZXJmtmCtx2uz9x3+0jR9wu8vViMBANu2pWUR3797/86GMwdqw8FuDYCKd0cQF6jbaIOp9vZtAy67wbwFVF9fzMCY095U/cLlmr1dwojTxZ2L9TtSavcBxKqrq53RGME5AMzLza2IiU+hgqeWfdUz+eZpQz70PuZBHgoE2gSLSJ2FLw2bVwMFsG1bBQKBLiE04XJpl0cVwDRNAoD4xLgT6RkZFbFJsRcAID8/X2G0jbHh+/aJQao2bP++/wA0SxpJxkrsDQAAAABJRU5ErkJggg==', 'blue64': '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', 'red32': 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAFA0lEQVR42sWXW2xUVRSG/733mZkzvbdDWzqpXGps7ACi0nqh4KBGKhpEgTOQImqQECM8+CKJjcmZA3iJiYkhglEg1RAMnQEJGE1paWpruAkEqlBoLUW52sqltA1zO3svH4rxrS3tgCvZz/tb/7/2WmsDyQ12+9z7ME2T4/+KUCgkAACG4SxasSKT/afGkDFaakZELBAIyGmB+eWruXbk5a7uWiLipmmyu605//eGNyorrYZP18vPZs+lxop5ZCxdsgwATL9fu2t+MwAozMh5/+1VtV3V2+ns+k1qxQMlid45hvpk3vxOmK/rNIyiHIkFLBgMEhVlZ368YHl91eP+irz0zMR3x35hYyRpnHE1XWkTX2qPLGAA+f1+kUwAZpqmYIzhvecW17xTWv4okzJhRyOO2mOHUZSShl6lMN5W9EhMLQGAlXl5lDQA0zSFZVn20lcr160qLa/gtkxwTXMc7exAS/sZcI0jqmwmpGT5NvlgGs5F4bAczIZhAxiGIdZYlj3zxYqK5VPKqrx6it0bj2lOl46NDXuRpQi+zBwADAMpE8MkX9KeIff5fETTise8Nrm0+qnCCdQTjfB0XWfnLl/EjkP78UxBIfJdbthKEuOCbgp2CQErrgayp1EBhEIhZlmWWjm1fN1i39SCaCwmiYg7dR1fNtYjEovi6XwvNM4hCNTnEKzTIRoBIDjaIjRNky8KBOTEGWXFz08oXpbGNRWVUuiahhs9PdjS1IASdyqmZGQjohS5GeOHmR3dm6ptYQAwa5YarQWcALxQPOUt/7giRzQRVyBibncKdh09hKs3ezCvcDyynDqEVLLX7eLNLr7hfPW3nTWGISzLGhRgqE7F1q5ZYwPQS/O8C9M1J3qjES44RyIRx+f7aqEzhmdzC2ATKTdnvI7La5vz3B8RwFg4rEZVhIZhcEWEJ+fOmf5wvvc+W9pKkeKpuhsH28/g+LmzmOnJxf1pGSA7QX+5XfwnnX2IDVuv3faehgIYVAGfz8cAoCzPO7so2wNbKkUEzjUN4cMHAAAVYwvh4kIpMF4vZHvNg6kbyTQ5syw56mkYnDSJAMCbmjE5zeFEQknmFAL9/X34/sQxpHCOaVkeCCmpQ9dYg86rmPVNNNDayoaT/dBFaBgEALoQ6TxhQykFt8uFX8//gT//7kJZlgfj9BRpa0I0CLm/bntoZ41hiPBA98PoAcJhBgBRkr3kzQcJDq5p+LntNADgMU8uxggNRxxAQ6a2mhEQvsPhMrgFp04xAOiO3epIFI4lh9NJkBL7O9rgALCwYJy86XSIfQ7advDrmgN3mv2QAK2trQQAxy9frG/7sY45bcUj8ThaLl1ASWoGTU7LZLt54nq1R3+XAB7whQnJVCAcDisiYo27f2ho7rpw1qHr7EZ/v7p0/RqeyMpRF1OcfI9LVd36atuVsGEwWFBJBQBAwWBQAIjVnWv/4MqtPhaNxZSMx+VDnlzRKGRLfcmuTSHDEIFhNJ0RtWLLsiSZJt+zY9fWPb+faum34xoAFc/KxG/ZqWuZBbWhu3vYz24ks4ACra2MAXbz1e43d7ad7MsQmuOkA60nv6jcTQBramqy78X6zwFgxswZ9Z60NHplTsVmAPCPcvPld7gP8kgk0mULIeOa83TSshougGVZKhKJ9glNE05dO3NPAYzbbTkzO6O5wOutT89JPzGwb8xSuNfBWPJ+XWKEqiXtJ/wPeBodhVa1D64AAAAASUVORK5CYII=', 'red64': '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'}
ICONS_PX = {'blue32': 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAADzklEQVR42tWWS2yUZRSGn/PfKkWmF2jSmnaKZRQkIdp4w8SYuhCnFZpgYvBu2GhIdOGSpS50Y4qJMcZFXbgzLhpAnGmigbowUQQLAYIp4NCmFDo4TGfo3P7/+44LNC6nl6GJZ/1957x5z3vec4QGx969e9V1XVpaWhgdHZV6751GA7i5aJiamqJYLLJmsWf3bu3r69N4T4+O/Gy0paVF+/v7dSl/vdUWHxoa1Pc+PcypObAIh3/K0trWxoYNG5b0f1UteGnfq/ryx99xIqNMnCty/MwCCKgq2ew8w8PDetcYePfgB7o+1kbVCIlNwi+TOQq5WdbHHmDdll00N1micLZuHllJ8cHBpB44dIyyES7cVHb1CS8++wSIy7b9Y4gIWrhC8+8fkkqPS8MZSKXS8s4Imi8rlUh4bluMRz+aIQwtizOXsCbEr95gnWrjNTCYTCpAviYUqxBZxaoliiy+64KNcFwPVYvruo0F8Mprr2sqnZavz1rNl8FzhRs5i40MagyCIo7L/Ng+Ns6Ocuz7VGONaEsiwcyC1UINZm8rV/8q8e1b9/L4J1magiYA8tlLdHRsIhaL0XAf6H1yD2MXFCMCCJXSAiYyOI5DJXsNG9Voam6lvb3BPpBMJvX45Ujvue8RKqFQi8AVpRqWEREES3Q7jynmCJrbCfwA3w8ax4DjCCIQBELPRpjOK4eGmmnq3MrTX5Sx+QUcwGjIrSNvcjqTWfJ412XghaEhff+zY2SKDrFAeaZHMRZUwWvtQkQpzWWoVStEBrZu27qsqarLgPJfwZkCTOXAcRRjLWoNCJgoRFDAoqqNBVAoFBCBioWFijBfUr4ZGcEYi83NYCKLrZUQHHDdxgMIfJ/LC2ANiCpqlevjBxn4vEC1FlH64zzieNw8+gaeK0z+mVmWvdfVgO8HGAMHHoPnE4Ir/EM2+L5gKkVEDQ9uf5h4PL5sW6/LgDgOZy9m+bWrg2tFxeidDaYoooAaqleO8mP6yIoWm7eUddndvYnTc7AYCo4oquALhNaA61O6OLbim6JuC1LptHy1v4/AtSyWqpw6eR0R5db5ScpT53GwbN/+0IoBLMmI7t+8mcwtJX9bCWvRHRGgmLBELvU2v129KneNAYATExMy/cOXzE+Ogzgg4LgBYiO6ujpXdVMueRu6cyfJnkmhqogINiyDE9De3s6axlM7d6rnedrd3a07duzQ1eZb9kUUGYOq0tvbSyKRYM0B/Gu1nuchImsPwBiDiBCFIQ2ov0LUjqNdnZ0aj8dXrYEVneUDAwNEUUQQ+ExPT/O/jr8BBce86ZfAzB8AAAAASUVORK5CYII=', 'blue64': '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', 'red32': 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAADyUlEQVR42tWWz2tcVRTHP+e+NzOdpLTJjNGmNW3QSIeg0JW0hBbpwsTWxKKloDtBLQHtSgzULotI0VXBIGK76T9QSzEpRhRLbE1ialJoGmKQBDq0dZpp2sy8N++9e1xM0eVMJpOAB97m3R/ny/ec7/ceoc7R39+v8XiciYkJrl69KpX2u/UGkJ25zcLDJaLIsmFx/PgHumfPHt21s03Ds9/qM+m0Njc1aTVn18xAT3e3fvX+R+grc0g2i//9RZqbtvLYL7GUz1c8b2pNPDAwoL29r+vl01/A6HXC66MUR4bACDFVHMfwRl+frhsDT29KsrkjA7kcGOGR73PT93g5meTVLVsIjWHG99enBD093Xri8Js4QYD+Pok4MQbzec7PzXKj8yU+27kLVDgSrBOAbwZOYSan0CAEY0idPMGnHS8wlXmRydzfuAasKjQ3178HDh06rDsat4IqiAUFYxxsECACMcOTf1LeU08G3jl2TC98fAodmyxnQdBb0xjXIa6CiJAwhqOLi4jr8ufor/U1opatTSAgKBr4RNbSdG6QuwcO4rgOijKTe0BLSwuRCMzP15eBt/Z2oeOTEAaItRhjsGoxCZcl32fZ99mcTNLY2IC61V1dVQ+81tOj4diUdj3bjvgeRBEqQBghCDiGh4Ui9z2PVCJOQ7KB5KYkdXNCEQGr4LqoBW1IkvrkQ2Kuy3LvEcJCAS+KeOAVOLG0xMK1a1ItqxUZ6Ovr00snTyN/3ISZOUgkkNCiCDYMscUiN/J57ntFVoKIzO7dq1JVRQCeV0RiBiILUu50NUIYhqgqoPiBz0poicvqlV2xBCW/BEGExBysXwKvyLmznxOWSoQoIobcSgEVkCdfXQFYtXB7FiKLOA4aM/QvLPKo9wjG8xjP5XBQLhSKjNuQv4aHpa4lSMTjaKTw3tvI4YOICmIMoiDxBPeW86gRnmvdRiaTWbWtm6oU4BfQ65Po9K2y/P5bRIDvfI8dXV0MDQ3LagFULIFxHLRQwIxNlK3dRv8mt0GAAX4KAs6fOSO1PGwVGRgaGpbnB78kNA66/Bjv5yuA8sP8LFcW5gmBzs7Omieqqoyoo6MDufEbVgxGFVWIGwdXhXfzORYuT0utAKoS7cjIj/L13SwX72XLDSjlx1CJaG3dtqaZsmrXuBT4/BKWUKuICJGABVKpFBsae/ftU9d1ta2tTdvb23Wt9616IgqDAFXlqXSadDrNhgMoh2Icp+wRGw1ARBAxqNq6AKhNu66j6XRKt29vXXMP1DSW799/AGstsViMO3ey/K/jHw34m6H8JdI1AAAAAElFTkSuQmCC', 'red64': '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'}   # пиксельные иконки для «Классической (системной)» темы
GLOBE = {'smooth': 'iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAFMklEQVR42kVVWWxUZRg9/39n60w7M+0wLZQOKSAUKJRCQtiXGBKBomxOEQj6gBENwfDQhAgxpagPSgyKlbiFhCCIHWMgLIaIARqqEShhEUqF0n1fZp97/3v/xYcCnuTky/dycr7k5HwEz6AUyAFUkxpSI3fX1wfh668sdnVUFPpS5VyRoJBSHWhY1GcwenvJ2P5fQ56lkcOLJuh1KqxVkoh4rkOei5HRTe3/57td2Xa+Vzntoa/vz8N7U+rxZkkzsmCgqmEBjjfORY4nCiG0B5O90f33t2w8i+pqipoaCQB01BnI8qtXtOupPSdXvNRX+yDuDc11dwqH25LDplflKIqvGmfjbodXlQdbZHLEkiyll25d+PeZo93vHiIHP5LhurAGBUIjCNMaQuUn83/+qUcr2Pr+5cXWeA9Tp3tmaa3JIG1KBciB22U4eGsFmvQgSTNJQRRVyZTUknFuwF51tHfzkUhlRNQhTAkAXIzv2jPJSw7X9xaYtQ+XO04vuwhD2rH1xlo8GioAzBQ0pUOkGRDn8NsGUVHcgkddmpo1oZcvernXrgke3uGN/ELOp6rG2rWhB1R6/JppJ4EsG/HZgesdftxOFKK2bRGkqYPrDERnIAaDgyUxO7sd6xa2YfbMLjkiOYkmzdaSgCizMT70lsdD88yEFPe6cumqqQlceDoWRx6WY4BnQ8o0uCkBS0BxAUgOg9kwSHOQl2Og4eYY6g8Oyj4zOOnPRv9qm6msdUzYlM3GyerSbnzfOBOH7y4BPARQALg1SnN0EsEBXWJxeQ/6h5w4ca4QOc4CNbl8RE0vfbKVtgx4y4TQCZRJr7bk4dvGUmgaAzXSIHoaMAzAMAGTjYpaFhQXuNfqwcRQHJ/uu4nCCSna3BQgI3HnAtu/fbkey1KoPbcc4wp1ZDIaIDLP0g5ASkCIUXeWBWUIBNwJ7F7fjEB+Bv0pgcrKe2TYNDAw7Mqj9Y8mYzBhh9fPkIxTTPW1I0ekoDEDlOnPHBqAwUAtBpUQWDq9E5OKouiPA0xyxDNAxhJI6cRGu2LjUlduTkbF9JuAMjHcR6DSaYiogExaIMx4RgZiMoAxuB1pZJQFoTFYlMGQpuI2Dkvj3Zrr1c0VvQPB0N2mHOV3Jcj6xU+wfXkzQrlxdPe5kIwTQFig3IQyOWBxxIYkpk3rRZJxxHUO4dCl4TCJEOY1Leu1LVmcqAorZqlYXCNvrLqD0Ng4SsYPY2V5Ozp7nejpdEHqEhAmwDniQ3Y0NHhx7VwRUkyheG4bRjKU6tH8D+i0YtsJAqOLOJ2gTMmOQSChdHQlBTLIYOfrN3Co6nfML22FisrR06EjmXAgHfMgw4kw3Trpflp498eyS+fpjTVrEj6/bR8NeqiQDnHs+Bzca3bAsicRtQwkoCM7OIiBHgWYDIoxKGaBKgGabanQnMcyYWQTGZuxHyCcoq5Oi+7ccCLHlT5GJ+bZE+kx1hefLZOPOzRkaApppHDhtwK0PvCBUB2KSxAqIXW3LJrbLkLzo/a2v8q+vLT28wvhurCmIVIHFS7VrMObz/g3bhovfO551nAWUegTJQubcOt6Ec5+M58Qt4BSUABVIA5FAz46a3ULjbUXf3z5lVN7w3WbtEhlRJL/i1aBgqjcH05vSw1q1TZzeMqq9Sfxx4mViPWMAbGbUJodxO0C9TrhCsg7+X72YeuOd85XK9AaAvmisV+gWlHUELlt6KL37Cmyxafd2mCYzrLYSH6QEA7i0PqcHscdX8AeeXv7jNM1ZKYZVtAiBC9ewH+Vo8weXYyR8AAAAABJRU5ErkJggg==', 'pixel': 'iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAE3UlEQVR42nWUWWxUdRSHvzv3znQ6M7TTobRDOwXaspTWUlCKYauiBksiW7REo6YkkopEo4mJ8QGj1Rif9VUTgyEmKiQEkKAs1aAstmBlaSltoXajM21nvXPnrvP3gZC44O/lnPPw+3KePokHpKOjwy3LocClwcHn3Ep2d4EiyANZXUGWCo401Fd9TjKoHzjQqf+7K/39aGtrk2OGsSoXrn539Rr/syP+BozaMvav/IZJJ8NHp3Yy1r8I/80rBLPDP5eo/a+1NjcPdHZ25u8zXPeX9vZ277gn9F5kx/LuPZ/Mf/ZG1Vp2bOhnMhnGFja/3CrHGPMjBYqZrnicpa/PeWzeM07fr6O/dXZ0dPj+AxxOGh+u3df6/q4Xi/iieyPlwSkuDEeYypTyR7KI7wb3kfBWY2UEGAbZjEK6oopIu2t/X2yi8z5HBnhkU+vm59/Z+9kT60/IcVXm6O21vLzqOAsW9fPHTBOHrmxDhMOo0xLexF22P9nFxYvNSHcGeXhLjqLFdrM0Vts7eWfolvxUW1vxvMeWfb1yl1wxyQBZrZgNtb/id6e5crUBS3IYlRoxJ1S4m8RHAiNhUlN9jZYXRtAKNKYKbNmIi6YG39qDSno2+1zTJl+TXzqHbPk4OriYjXXd/HBjLt0DDzFkrgGRhoQGqkbKDqDPLKS+qo+LXWFs4eDyZ/GFlfpoanS7korU7xblM4wLDZ9is37FOU50reDHa9ugPATChqQKOQMsC0wTlxrH47WZvFRHQSBDbkahced5CvvEHsW2xIaY7sGeDtB7cRWlxbOcufQkVBSBZkBKBU0H0wTbBsMkNCfHqsUqjS2n6Omdx8hQkNhdP8KVblGEJTNwox6XphJPVxIdCxJwxUj9KUAAeefetG2wbRRT5c23zhGoiZJ28pTW3yZYB5fPhMnrAhcuF9f611BbP0Jr60nGR8P43HG8RvTeVwIwDXAssGwioRjhpdNkhcNETse0IZoCT0jFcWTkkuXrPpgpbeF6TyOpaQ9zixNUB1V2ru/FK00xE/Vg5hQwHTAtshlBcOFtMv4ksRk3CcPBcgTZlCB9shh5fmRJU7po2XIbhdlkmPiEn7df/Z4ldVFqV4xSVjnCjQvl2IYMpkHezHP17Hyu/7iUW6crKW2cQDNskqMulJ7CQ645VvSYosaEZJmgaWA7TLpmGbSyzAqL4ppJtu49TENjF5KaQZgmjnCjqV5M3Y0uLHKaIDU2R/ic1BF5YmSoN1y5aEvaWxMh7yCsPB4pTsWyKDOaie44SH6dTFwwdrUWHAPJyoFtgmlQtGyCtGnh/sl/uf/ksTdkgIaq0GXLcnZkxbwAlsXw72VkplV8S6IMR/MMdZfQf3gFtgqSkQPdBMOi5pVLJDxpxLGl05FY/KXxO4MTMsD4nYGpuqpQ1LLtnRolSHmdbFKn6NEREre9XP90E5bhRZgGkm0jBCArFGy4idw1l/LR5Js9Z48d/4dtuk99ezBiXF63IHV6ULYSaNNFaCqM/1CLEAIMHRznnkS9PqSSUjxflQ2HB/SW7RtXfvlAwQKs3ri5atYJfZykeiu1WjBXmsP4pQZkDwgJr6zhqSxMBfTJ3jK1r/33rhN//q+x/57mTU83ZA3vE6LQeF7KyuCSEHlBocd9wGVlz/dcOHX9Qb2/AGv7bxYMy7gxAAAAAElFTkSuQmCC'}   # вкладка «Язык»: гладкий и пиксельный глобус, 20x20
PROGRESS_RE = re.compile(r"(?<!\d)(\d{1,3})%")


# ------------------------------------------------------------------ утилиты

def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def make_logger(base_log):
    """Оборачивает вывод: дублирует сообщения в portabilizer.log."""
    path = app_dir() / "portabilizer.log"

    def log(msg):
        base_log(msg)
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
        except Exception:
            pass
    return log


def fmt_size(n) -> str:
    n = float(n)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or unit == "ГБ":
            return f"{int(n)} {tr(unit)}" if unit == "Б" else f"{n:.1f} {tr(unit)}"
        n /= 1024
    return str(n)


def fmt_time(sec) -> str:
    sec = int(max(0, sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def existing_parent(p: Path) -> Path:
    """Ближайшая существующая папка вверх по дереву (для проверки свободного места)."""
    p = Path(p)
    while not p.exists() and p != p.parent:
        p = p.parent
    return p


def _extra_tool_dirs(names):
    """Где ещё искать: установленный 7-Zip (папки Program Files, реестр) и 7-Zip Portable
    в Загрузках, на рабочем столе и в домашней папке. Только чтение, ничего не копируем."""
    dirs = []
    if any(n.lower().startswith(("7z", "7-z")) for n in names):
        for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)", "LOCALAPPDATA"):
            root = os.environ.get(var)
            if root:
                dirs += [Path(root) / "7-Zip", Path(root) / "Programs" / "7-Zip"]
        if os.name == "nt":
            try:
                import winreg
                for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    for sub in ("SOFTWARE\\7-Zip", "SOFTWARE\\WOW6432Node\\7-Zip"):
                        for val in ("Path64", "Path"):
                            try:
                                with winreg.OpenKey(hive, sub) as k:
                                    dirs.append(Path(winreg.QueryValueEx(k, val)[0]))
                            except OSError:
                                pass
            except ImportError:
                pass
        home = Path(os.environ.get("USERPROFILE") or Path.home())
        for top in (home / "Downloads", home / "Desktop", home):
            for pat in ("*/App/7-Zip64", "*/*/App/7-Zip64", "*/App/7-Zip", "7-Zip*", "7z*"):
                try:
                    dirs += [d for d in top.glob(pat) if d.is_dir()]
                except OSError:
                    pass
    return dirs


def find_tool(*names):
    """Ищем утилиту рядом с программой, в tools/, в PATH, затем (для 7-Zip) в установленном
    7-Zip и 7-Zip Portable. 7z.exe без 7z.dll рядом не годится: он не запустится."""
    bases = [app_dir(), app_dir() / "tools"]
    if hasattr(sys, "_MEIPASS"):
        bases.append(Path(sys._MEIPASS))

    def usable(p: Path) -> bool:
        if not p.is_file():
            return False
        return p.name.lower() != "7z.exe" or (p.parent / "7z.dll").is_file()

    for base in bases:
        for n in names:
            if usable(base / n):
                return str(base / n)
    for n in names:
        p = shutil.which(n)
        if p and usable(Path(p)):
            return p
    for base in _extra_tool_dirs(names):
        for n in names:
            if usable(base / n):
                return str(base / n)
    return None


def dir_size(folder: Path) -> int:
    total = 0
    for p in Path(folder).rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def detect_type(exe: Path) -> str:
    """Определение типа по расширению, затем по сигнатурам в файле.

    Возвращает: msi, msix, archive, inno, nsis, wix или plain.
    """
    suffix = exe.suffix.lower()
    if suffix == ".msi":
        return "msi"
    if suffix in MSIX_EXT:
        return "msix"
    if suffix in ARCHIVE_EXT:
        return "archive"
    with open(exe, "rb") as f:
        head = f.read(4 * 1024 * 1024)
        f.seek(max(0, exe.stat().st_size - 1024 * 1024))
        tail = f.read()
    if head.startswith(ARCHIVE_MAGIC):
        return "archive"
    blob = head + tail
    if b"Inno Setup" in blob or b"JR.Inno.Setup" in blob:
        return "inno"
    if b"Nullsoft" in blob or b"NullsoftInst" in blob:
        return "nsis"
    if b"WiX" in blob or b"Wix Toolset" in blob:
        return "wix"
    return "plain"


def clean_stem(p: Path) -> str:
    """Имя для папки *_portable: без расширения архива и без .partN."""
    name = p.name
    low = name.lower()
    for ext in (".tar.gz", ".tar.xz", ".tar.bz2"):
        if low.endswith(ext):
            name = name[:-len(ext)]
            break
    else:
        name = p.stem
    name = re.sub(r"\.part0*\d+$", "", name, flags=re.I)
    return name.strip(" .") or p.stem or "app"


# ------------------------------------------------- управление задачей (Job)

class JobCancelled(Exception):
    """Пользователь прервал задачу."""


def _suspend_tree(proc):
    """Замораживает процесс и потомков. Возвращает список замороженного (для продолжения)."""
    frozen = []
    if psutil:
        try:
            parent = psutil.Process(proc.pid)
            for p in [parent] + parent.children(recursive=True):
                try:
                    p.suspend()
                    frozen.append(p)
                except psutil.Error:
                    pass
        except psutil.Error:
            pass
        return frozen
    if os.name == "nt":
        try:
            import ctypes
            fn = ctypes.windll.ntdll.NtSuspendProcess
            fn.argtypes = [ctypes.c_void_p]
            h = int(proc._handle)
            if fn(h) == 0:
                frozen.append(h)
        except Exception:
            pass
    return frozen


def _resume_tree(frozen):
    for p in frozen:
        if isinstance(p, int):
            try:
                import ctypes
                fn = ctypes.windll.ntdll.NtResumeProcess
                fn.argtypes = [ctypes.c_void_p]
                fn(p)
            except Exception:
                pass
        else:
            try:
                p.resume()
            except Exception:
                pass


def _kill_tree(proc):
    if proc.poll() is not None:
        return
    if psutil:
        try:
            parent = psutil.Process(proc.pid)
            for p in parent.children(recursive=True) + [parent]:
                try:
                    p.kill()
                except psutil.Error:
                    pass
            return
        except psutil.Error:
            pass
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, creationflags=CREATE_NO_WINDOW)
    else:
        proc.kill()


class Job:
    """Одна конвертация: пауза, продолжение, отмена, прогресс и контроль места на диске."""

    def __init__(self, auto_cancel_on_low_space=False, on_event=None):
        self.proc = None
        self.cancelled = False
        self.paused = False
        self.pause_reason = ""
        self.progress = None            # 0..100 или None, если процент неизвестен
        self.stage = ""
        self.started = time.time()
        self.finished = False
        self.watch_path = None
        self.expected_total = None      # сколько всего будет записано (если известно), байт
        self.override_floor = None      # после «Продолжить»: порог паузы вместо обычного
        self.auto_cancel = auto_cancel_on_low_space
        self.on_event = on_event or (lambda kind, text: None)
        self.paused_total = 0.0
        self._pause_started = 0.0
        self._suspended = []
        self._lock = threading.Lock()

    # --- процесс
    def attach(self, proc):
        with self._lock:
            self.proc = proc
            self.progress = None
        if self.cancelled:
            _kill_tree(proc)

    def detach(self):
        with self._lock:
            self.proc = None

    # --- управление
    def pause(self, reason="user") -> bool:
        with self._lock:
            proc = self.proc
            if self.paused or proc is None or proc.poll() is not None:
                return False
            frozen = _suspend_tree(proc)
            if not frozen:
                return False
            self._suspended = frozen
            self.paused = True
            self.pause_reason = reason
            self._pause_started = time.time()
            return True

    def resume(self) -> bool:
        with self._lock:
            if not self.paused:
                return False
            _resume_tree(self._suspended)
            self._suspended = []
            self.paused = False
            self.pause_reason = ""
            self.paused_total += time.time() - self._pause_started
            return True

    def cancel(self):
        self.cancelled = True
        with self._lock:
            proc = self.proc
            if proc is not None:
                _kill_tree(proc)
            self._suspended = []
            if self.paused:
                self.paused_total += time.time() - self._pause_started
            self.paused = False

    @property
    def active_elapsed(self) -> float:
        now = time.time()
        extra = (now - self._pause_started) if self.paused else 0.0
        return max(0.0, now - self.started - self.paused_total - extra)

    def force_resume(self, floor=HARD_FLOOR) -> bool:
        """Продолжить, несмотря на малое место: пауза сработает снова только ниже floor."""
        self.override_floor = floor
        return self.resume()

    def remaining_bytes(self):
        """Сколько ещё осталось записать (примерно). None, если оценить нельзя."""
        if not self.expected_total or self.progress is None:
            return None
        return int(self.expected_total * (100 - self.progress) / 100)

    def free_bytes(self):
        try:
            return shutil.disk_usage(existing_parent(self.watch_path)).free
        except (OSError, TypeError):
            return None

    # --- контроль места
    def watch(self, path):
        self.watch_path = Path(path)
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def _watch_loop(self):
        episode = False                 # уже сообщали о нехватке места в этом «эпизоде»
        last_free, last_t = None, 0.0
        while not self.finished and not self.cancelled:
            time.sleep(WATCH_INTERVAL)
            try:
                free = shutil.disk_usage(existing_parent(self.watch_path)).free
            except OSError:
                continue
            now = time.time()
            rate = 0.0                  # как быстро убывает место, байт/с
            if last_free is not None and now > last_t and not self.paused:
                rate = max(0.0, (last_free - free) / (now - last_t))
            last_free, last_t = free, now
            # запас: сколько успеет записаться за три интервала проверки
            if self.override_floor is not None and free >= LOW_SPACE * 3:
                self.override_floor = None          # место освободили - обычные правила
            if self.override_floor is not None:
                margin = self.override_floor        # пользователь решил дотянуть до конца
            else:
                margin = LOW_SPACE + rate * WATCH_INTERVAL * 3
            if free >= LOW_SPACE * 1.5 and free >= margin:
                episode = False
            if free < margin and self.proc is not None and not self.paused:
                text = (f"На диске {existing_parent(self.watch_path).anchor or self.watch_path} "
                        f"осталось только {fmt_size(free)}.")
                if self.auto_cancel:
                    self.on_event("low_space_cancel", text)
                    self.cancel()
                    return
                if self.pause("low_space") and (not episode or self.override_floor is not None):
                    episode = True
                    self.on_event("low_space", text)


# ------------------------------------------------------------- запуск программ

def run(cmd, log, ok_codes=(0,), job=None, track_progress=False):
    """Запуск с захватом вывода. cmd - список или готовая строка (Windows).

    stdin закрыт: программы, которые просят пароль, не зависают, а завершаются с ошибкой.
    Если передан job, процесс можно поставить на паузу или прервать. Хвост вывода - в run.last,
    код возврата - в run.rc.
    """
    shown = cmd if isinstance(cmd, str) else " ".join(
        f'"{c}"' if " " in str(c) else str(c) for c in cmd)
    log("> " + shown)
    try:
        dec = codecs.getincrementaldecoder("oem" if os.name == "nt" else "utf-8")(errors="replace")
    except LookupError:
        dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
    if job:
        job.attach(proc)
    tail = ""
    try:
        while True:
            data = proc.stdout.read1(4096)
            if not data:
                break
            text = dec.decode(data)
            tail = (tail + text)[-8000:]
            if track_progress and job:
                found = PROGRESS_RE.findall(text)
                if found:
                    job.progress = min(100, int(found[-1]))
        rc = proc.wait()
    finally:
        if job:
            job.detach()
    if job and job.cancelled:
        raise JobCancelled()
    # убираем строки прогресса вида " 37% 12 - file" из лога
    clean = re.sub(r"[ \t]*\d{1,3}%[^\r\n]*", "", tail)
    clean = "\n".join(l for l in clean.replace("\r", "\n").splitlines() if l.strip())
    run.last = clean
    run.rc = rc
    if clean.strip():
        log(clean.strip()[-1500:])
    return rc in ok_codes


run.last = ""
run.rc = 0


def archive_unpacked_size(src: Path):
    """Размер содержимого архива в байтах по `7z l` (None, если узнать не удалось)."""
    tool = find_tool("7z.exe", "7za.exe", "7z", "7zz")
    if not tool:
        return None
    try:
        p = subprocess.run([tool, "l", "-y", str(src)], capture_output=True, text=True,
                           errors="replace", creationflags=CREATE_NO_WINDOW,
                           stdin=subprocess.DEVNULL, timeout=180)
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in reversed(p.stdout.splitlines()):
        m = re.search(r"(\d+)\s+(?:\d+\s+)?\d+ files?", line)
        if m:
            return int(m.group(1))
    return None


# ----------------------------------------------------------- оценка места

def preflight(src: Path, out_root, mode="auto", radical=False):
    """Оценивает, хватит ли места. Возвращает dict(level=ok|warn|danger, text, need, free)."""
    res = {"level": "ok", "text": "", "need": 0, "free": 0, "exact": False, "total": 0}
    if mode == "launcher":
        return res
    src = Path(src)
    try:
        size = src.stat().st_size
        kind = detect_type(src)
    except OSError:
        return res
    note, exact = "", False
    if kind == "archive":
        unpacked = archive_unpacked_size(src)
        if unpacked:
            need_min = need_likely = unpacked
            exact = True
        else:
            need_min, need_likely = size, int(size * 1.3)
        note = " Если внутри архива установщик, понадобится ещё примерно столько же."
    else:
        bins = 0
        if kind in ("inno", "nsis"):
            bins = sum(b.stat().st_size for b in src.parent.glob("*.bin"))
        base = size + bins
        if kind == "plain":
            need_min = need_likely = size
            if radical and same_drive(src, out_root):
                need_min = need_likely = 0          # режим R: файл переносится, а не копируется
        elif kind == "msix":
            need_min, need_likely = size, int(size * 2.5)
        else:
            need_min, need_likely = base, int(base * 2.5)
    try:
        free = shutil.disk_usage(existing_parent(Path(out_root).resolve())).free
    except OSError:
        return res
    drive = Path(out_root).resolve().anchor or str(out_root)
    res.update(need=need_likely, free=free, exact=exact, total=need_likely)
    how = "по содержимому архива" if exact else "ориентировочно"
    base_text = (f"Нужно {how} {fmt_size(need_likely)}, свободно {fmt_size(free)} на диске {drive}."
                 f"{note}")
    if free < need_min:
        res.update(level="danger", text="Места, скорее всего, не хватит. " + base_text)
    elif free < need_likely + LOW_SPACE:
        res.update(level="warn", text="Места впритык: запаса почти нет, задача может "
                                      "встать на паузу. " + base_text)
    return res


# ---------------------------------------------------------------- история

class History:
    """Журнал конвертаций в portabilizer_history.json (рядом с программой)."""

    def __init__(self, path=None):
        self.path = Path(path) if path else app_dir() / HISTORY_FILE
        self.lock = threading.RLock()
        self.items = []
        self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            items = data.get("items", []) if isinstance(data, dict) else []
        except (OSError, ValueError):
            items = []
        for it in items:
            if it.get("status") in ("running", "paused"):   # программу закрыли посреди работы
                it["status"] = "interrupted"
                it["finished"] = it.get("finished") or now_iso()
        self.items = items

    def save(self):
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            tmp.write_text(json.dumps({"version": 1, "items": self.items},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            pass

    def add(self, **fields) -> dict:
        with self.lock:
            rec = {"id": uuid.uuid4().hex[:8]}
            rec.update(fields)
            self.items.append(rec)
            self.save()
            return dict(rec)

    def update(self, rec_id, **fields):
        with self.lock:
            for it in self.items:
                if it.get("id") == rec_id:
                    it.update(fields)
                    break
            self.save()

    def remove(self, rec_id):
        with self.lock:
            self.items = [i for i in self.items if i.get("id") != rec_id]
            self.save()

    def get(self, rec_id):
        with self.lock:
            for it in self.items:
                if it.get("id") == rec_id:
                    return dict(it)
        return None

    def all(self):
        with self.lock:
            return [dict(i) for i in self.items]


STATUS_RU = {"running": "идёт", "paused": "пауза", "done": "готово", "failed": "ошибка",
             "canceled": "прервано", "interrupted": "прервано (приложение закрыли)"}


# --------------------------------------------------------------- удаление

def _force_remove(func, path):
    """Снимает атрибут «только чтение» и повторяет удаление."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def is_deletable_target(target: Path) -> bool:
    """Можно ли удалять папку как портативную копию: только то, что похоже на нашу работу."""
    try:
        t = Path(target).resolve()
    except OSError:
        return False
    if not t.is_dir() or not t.name.lower().endswith("_portable"):
        return False
    if t == Path(t.anchor) or len(t.parts) < 2:
        return False
    return (t / MARKER).is_file() or ((t / "Launch.bat").is_file() and (t / "App").is_dir())


def delete_target(target: Path, log) -> bool:
    """Удаляет портативную копию целиком. Возвращает True, если папки больше нет."""
    t = Path(target).resolve()
    if not is_deletable_target(t):
        log(f"Не удаляю {t}: папка не похожа на созданную Portabilizer.")
        return False
    if sys.version_info >= (3, 12):
        shutil.rmtree(t, onexc=lambda func, path, exc: _force_remove(func, path))
    else:
        shutil.rmtree(t, onerror=lambda func, path, exc: _force_remove(func, path))
    return not t.exists()


def source_group(src: Path):
    """Файл-источник и, для многотомных архивов (.part1.rar), все его тома."""
    src = Path(src)
    m = re.match(r"^(.*)\.part0*\d+(\.[^.]+)$", src.name, re.I)
    if m:
        pat = re.compile(r"^" + re.escape(m.group(1)) + r"\.part0*\d+" + re.escape(m.group(2)) + r"$",
                         re.I)
        try:
            files = [p for p in src.parent.iterdir() if p.is_file() and pat.match(p.name)]
        except OSError:
            files = []
        if files:
            return sorted(files)
    return [src]


def reveal(path: Path) -> bool:
    """Показывает файл или папку в проводнике."""
    path = Path(path)
    try:
        if os.name == "nt":
            if path.is_file():
                subprocess.Popen(["explorer", f"/select,{path}"])
            else:
                os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path.parent if path.is_file() else path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent if path.is_file() else path)])
        return True
    except Exception:
        return False


# ----------------------------------------------------------- рекомендации

TIP_RULES = [
    (re.compile(r"DX_fix\.bat"), "warn",
     "Игре на Unreal Engine могут понадобиться библиотеки DirectX (June 2010). Если при запуске "
     "появится ошибка про xinput1_3.dll, X3DAudio1_7.dll или XAPOFX1_5.dll, запустите DX_fix.bat "
     "в папке результата: права администратора не нужны."),
    (re.compile(r"Исходный файл НЕ удалён"), "info",
     "Радикальный режим не удалил исходный файл, потому что не всё удалось проверить "
     "(причина в логе). Портативная папка создана, исходник на месте: проверьте её и удалите "
     "исходник сами."),
    (re.compile(r"Нужен \.NET"), "warn",
     "Программе нужен .NET, которого нет на этом компьютере. Запустите Install_dotnet.bat в папке "
     "результата (он скачает рантайм внутрь портативной копии, без прав администратора)."),
    (re.compile(r"парол|password", re.I), "warn",
     "Файл просит пароль. Portabilizer пароли не вводит: распакуйте его вручную в 7-Zip "
     "(он спросит пароль) и выберите установщик или папку из результата."),
    (re.compile(r"Нужен 7z\.exe"), "danger",
     "Не найден 7z.exe (ни рядом с программой, ни в установленном 7-Zip). Установите 7-Zip с 7-zip.org или положите 7z.exe и 7z.dll рядом с Portabilizer или в папку tools."),
    (re.compile(r"Нужен innoextract"), "danger",
     "Не найден innoextract.exe. Положите его рядом с Portabilizer или в папку tools."),
    (re.compile(r"not enough space|No space left|disk is full|недостаточно места|ERROR_DISK_FULL",
                re.I), "danger",
     "На диске не хватило места. Освободите место или выберите другой диск в поле «Куда», "
     "затем во вкладке «История» нажмите «Повторить»."),
    (re.compile(r"Без админа не вышло"), "warn",
     "Установщик требует права администратора. Если их нет, попробуйте режим «Только распаковка» "
     "или поищите у разработчика портативную версию."),
    (re.compile(r"Главный exe не найден"), "warn",
     "Главный exe не найден. В логе выше перечислены найденные exe и причина отсева: скопируйте нужное имя в поле «Главный exe» и запустите режим «Только Launch.bat»."),
    (re.compile(r"UWP"), "warn",
     "Похоже на UWP-приложение: вне установленного пакета оно, скорее всего, не запустится. "
     "Поищите exe-установщик."),
    (re.compile(r"Не удалось распаковать"), "warn",
     "Проверьте, что файл скачан полностью (сверьте размер или скачайте заново) "
     "и что 7z.exe лежит рядом с программой."),
    (re.compile(r"Папка уже есть"), "info",
     "Эта папка уже создана раньше. Откройте её во вкладке «История» или удалите, "
     "если хотите начать заново."),
    (re.compile(r"похоже на репак"), "info",
     "Данные лежат во внешних .bin файлах, их ставит сам установщик. Для этого может понадобиться "
     "установка, а для неё - права администратора."),
    (re.compile(r"Прервано пользователем"), "info",
     "Частично созданные файлы остались на диске. Удалить их можно во вкладке «История»."),
]


class Advisor:
    """Хранит последние рекомендации и не повторяет одну и ту же слишком часто."""

    def __init__(self, on_change=None):
        self.items = collections.deque(maxlen=6)
        self.on_change = on_change
        self._last = {}

    def add(self, level, text, key=None, cooldown=45):
        key = key or text
        now = time.time()
        if now - self._last.get(key, 0) < cooldown:
            return
        self._last[key] = now
        same = [it for it in self.items if it[2] == text]      # такая подсказка уже есть: обновим
        for it in same:
            self.items.remove(it)
        self.items.append((now, level, text))
        if self.on_change:
            try:
                self.on_change()
            except Exception:
                pass

    def scan(self, msg):
        for rx, level, text in TIP_RULES:
            if rx.search(msg):
                self.add(level, text)


# --------------------------------------------------------------- диагностика

def _quick(cmd, timeout=4) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                           timeout=timeout, creationflags=CREATE_NO_WINDOW,
                           stdin=subprocess.DEVNULL)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def cpu_name() -> str:
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    return platform.processor() or platform.machine() or "н/д"


def gpu_names():
    names = []
    if os.name == "nt":
        out = _quick(["powershell", "-NoProfile", "-Command",
                      "(Get-CimInstance Win32_VideoController).Name"], 10)
        names = [l.strip() for l in out.splitlines() if l.strip()]
    if not names:
        out = _quick(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], 4)
        names = [l.strip() for l in out.splitlines() if l.strip()]
    return names


def gpu_load():
    """Нагрузка GPU: nvidia-smi, а на других видеокартах (Windows) - оценка по 3D-движкам."""
    out = _quick(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,"
                  "temperature.gpu", "--format=csv,noheader,nounits"], 3)
    if out:
        try:
            u, mu, mt, tmp = [x.strip() for x in out.splitlines()[0].split(",")]
            return {"util": float(u), "mem_used": int(float(mu)) * 1024 * 1024,
                    "mem_total": int(float(mt)) * 1024 * 1024, "temp": float(tmp),
                    "source": "nvidia-smi"}
        except ValueError:
            pass
    if os.name == "nt":
        ps = ("(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine "
              "-ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*engtype_3D*' } | "
              "Measure-Object -Property UtilizationPercentage -Sum).Sum")
        out = _quick(["powershell", "-NoProfile", "-Command", ps], 8)
        try:
            return {"util": min(100.0, float(out.replace(",", "."))), "source": "windows"}
        except ValueError:
            pass
    return None


def list_drives():
    """[(диск, всего, занято, свободно)] для доступных дисков."""
    out = []
    if psutil:
        for part in psutil.disk_partitions(all=False):
            if "cdrom" in part.opts.lower() or not part.fstype:
                continue
            try:
                u = shutil.disk_usage(part.mountpoint)
            except OSError:
                continue
            out.append((part.mountpoint, u.total, u.used, u.free))
    elif os.name == "nt":
        import string
        for ch in string.ascii_uppercase:
            root = f"{ch}:\\"
            if os.path.exists(root):
                try:
                    u = shutil.disk_usage(root)
                    out.append((root, u.total, u.used, u.free))
                except OSError:
                    pass
    else:
        u = shutil.disk_usage("/")
        out.append(("/", u.total, u.used, u.free))
    return out


# --------------------------------------------------- распаковка и установка

def extract(exe: Path, kind: str, out: Path, log, job=None) -> bool:
    out.mkdir(parents=True, exist_ok=True)
    if job:
        job.stage = "Распаковка"
    if kind == "inno":
        tool = find_tool("innoextract.exe", "innoextract")
        if not tool:
            log("Нужен innoextract.exe (положите рядом или в tools/).")
            return False
        ok = run([tool, "-e", "-d", str(out), str(exe)], log, job=job)
        app = out / "app"          # innoextract кладёт файлы в app/
        if ok and app.is_dir():
            for item in app.iterdir():
                shutil.move(str(item), str(out / item.name))
            app.rmdir()
        return ok
    if kind in ("msi", "wix") and os.name == "nt" and exe.suffix.lower() == ".msi":
        # административная распаковка, ничего не ставит в систему
        return run(["msiexec", "/a", str(exe), "/qn", f"TARGETDIR={out}"], log, job=job)
    tool = find_tool("7z.exe", "7za.exe", "7z", "7zz")
    if not tool:
        log("Нужен 7z.exe: не найден ни рядом с программой, ни в установленном 7-Zip. "
            "Установите 7-Zip (7-zip.org) или положите 7z.exe и 7z.dll рядом или в tools/.")
        return False
    log(f"Распаковщик: {tool}")
    # код 1 у 7z - предупреждения (например, часть файлов занята), распаковка при этом выполнена
    cmd = [tool, "x", "-y", "-bsp1", f"-o{out}", str(exe)]
    ok = run(cmd, log, ok_codes=(0, 1), job=job, track_progress=True)
    if not ok and run.rc == 7:      # старый 7z не знает ключ -bsp1 (прогресс)
        cmd.remove("-bsp1")
        ok = run(cmd, log, ok_codes=(0, 1), job=job)
    if ok and run.rc == 1:
        EXTRACT_WARNINGS.append("7-Zip, код 1")
    if not ok and "password" in run.last.lower():
        log("Файл защищён паролем. Portabilizer пароли не вводит: распакуйте его вручную "
            "(7-Zip сам спросит пароль), затем выберите распакованную папку или установщик.")
    return ok


SKIP = ("unins", "uninst", "uninstall", "setup", "vcredist", "vc_redist",
        "dxsetup", "dxwebsetup", "crashpad", "crashreport", "update",
        "facompress", "precomp", "cls-", "oalinst", "physx", "dotnet", "redist",
        "subprocess", "prereq")
# короткие имена сравниваем целиком, чтобы не отсеять игры вроде "ArcheAge.exe"
SKIP_EXACT = ("xtool", "srep", "arc", "unarc", "7z", "7za", "zpaq", "lzma")
# служебные установщики, которые не надо принимать за основной установщик в архиве
INSTALLER_JUNK = ("unins", "vcredist", "vc_redist", "dxsetup", "dxwebsetup",
                  "dotnet", "redist", "physx", "oalinst", "crashpad")


def install_args(kind: str, app: Path) -> str:
    """Аргументы установщика одной строкой, с правильными кавычками.

    NSIS: /D= обязан быть последним и БЕЗ кавычек (пробелы в пути допустимы).
    Inno: путь с пробелами берём в кавычки внутри /DIR="...".
    """
    if kind == "nsis":
        return f"/S /D={app}"
    return ('/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /SP- '
            f'/CURRENTUSER /DIR="{app}"')


def silent_install(exe: Path, kind: str, app: Path, log, job=None) -> bool:
    """Тихая установка прямо в папку App."""
    app.mkdir(parents=True, exist_ok=True)
    if job:
        job.stage = "Установка"
    argstr = install_args(kind, app)
    log("Тихая установка в папку App (может занять много минут, не закрывайте окно)...")

    # 1) без прав администратора: RunAsInvoker не даёт установщику запросить повышение.
    #    Командную строку передаём одной строкой, чтобы subprocess не переэкранировал кавычки.
    env = dict(os.environ, __COMPAT_LAYER="RunAsInvoker")
    cmdline = f'"{exe}" {argstr}'
    log("> " + cmdline)
    ok = False
    try:
        proc = subprocess.Popen(cmdline, cwd=str(exe.parent), env=env)
        if job:
            job.attach(proc)
        try:
            ok = proc.wait() == 0
        finally:
            if job:
                job.detach()
    except OSError as e:
        log(f"Запуск без админа не удался: {e}")
    if job and job.cancelled:
        raise JobCancelled()
    if ok and any(app.iterdir()):
        return True

    # 2) запасной вариант: запрос UAC
    log("Без админа не вышло - пробую с запросом UAC (нажмите 'Да'). "
        "Остановить установщик, запущенный с правами администратора, отсюда нельзя.")
    ps_args = argstr.replace("'", "''")
    ps = (f"Start-Process -FilePath '{exe}' -ArgumentList '{ps_args}' "
          f"-WorkingDirectory '{exe.parent}' -Verb RunAs -Wait")
    ok = run(["powershell", "-NoProfile", "-Command", ps], log, job=job)
    if not ok:
        log("Установщик завершился с ошибкой. Проверьте, что .bin файлы лежат рядом с setup.exe.")
    return ok and any(app.iterdir())


def is_gui_exe(p: Path) -> bool:
    """True для GUI-программ (Subsystem=2). Консольные утилиты (XTool и т.п.) отсеиваем."""
    try:
        with open(p, "rb") as f:
            f.seek(0x3C)
            pe = struct.unpack("<I", f.read(4))[0]
            f.seek(pe + 24 + 68)  # Subsystem в optional header
            return struct.unpack("<H", f.read(2))[0] == 2
    except Exception:
        return True


# имена, которые не отсеиваем совсем, но ставим в конец очереди: патчеры, обновлялки, помощники
SOFT_PENALTY = ("patch", "benchmark", "crashhandler", "helper", "ffmpeg", "merger")   # "update" отсеян жёстко (SKIP)


def unreal_rank(p: Path) -> int:
    """2 - корневой exe игры на Unreal Engine, 1 - exe из Binaries (...-Shipping.exe), 0 - прочее.

    Корневой exe узнаём по структуре: рядом с X.exe лежит папка X\\Binaries\\<платформа>\\X-...-Shipping.exe.
    """
    try:
        if any((p.parent / p.stem / "Binaries").glob("*/*-Shipping.exe")):
            return 2
    except OSError:
        pass
    return 1 if p.name.lower().endswith("-shipping.exe") else 0


def exe_reject_reason(p: Path, folder: Path, allow_console=False):
    """Почему exe не годится в главные (None - годится)."""
    low = p.name.lower()
    # путь ВНУТРИ папки программы: если сама папка назначения лежит в ...\tmp\..., это не мешает
    rel = "\\" + str(p.relative_to(folder)).lower().replace("/", "\\")
    if any(s in low for s in SKIP):
        return "служебное имя (setup/update/redist и т.п.)"
    if p.stem.lower() in SKIP_EXACT:
        return "служебная утилита репака"
    if "$pluginsdir" in rel or "\\tmp\\" in rel:
        return "временная папка установщика"
    if not allow_console and unreal_rank(p) == 0 and not is_gui_exe(p):
        return "консольная программа"
    return None


def _size(p: Path) -> int:
    try:
        return p.stat().st_size
    except OSError:
        return 0


def exe_rank_key(p: Path, folder: Path):
    """Чем больше ключ, тем лучше кандидат: Unreal, не патчер, ближе к корню, крупнее."""
    low = p.name.lower()
    return (unreal_rank(p), not any(w in low for w in SOFT_PENALTY),
            -len(p.relative_to(folder).parts), _size(p))


def rank_exes(folder: Path, allow_console=False):
    """Подходящие exe, лучший первым."""
    cands = [p for p in folder.rglob("*.exe") if exe_reject_reason(p, folder, allow_console) is None]
    cands.sort(key=lambda p: exe_rank_key(p, folder), reverse=True)
    return cands


def find_main_exe(folder: Path, log=None, chooser=None):
    """Главный exe. Сначала только графические программы; если таких нет - допускаем консольные.

    chooser(options) - необязательная функция выбора, options = [(подпись, путь), ...];
    вызывается только если несколько кандидатов равны по приоритету (кроме Unreal-игр).
    """
    for allow_console in (False, True):
        cands = rank_exes(folder, allow_console)
        if not cands:
            continue
        best = cands[0]
        if allow_console and log:
            log(f"Графических программ не нашлось, беру консольную: "
                f"{best.relative_to(folder)}. Если это не игра, укажите exe вручную.")
        key0 = exe_rank_key(best, folder)[:3]
        tied = [c for c in cands if exe_rank_key(c, folder)[:3] == key0]
        if chooser and len(tied) > 1 and key0[0] == 0:
            options = [(f"{c.relative_to(folder)}  ({fmt_size(_size(c))})", c) for c in tied[:8]]
            try:
                picked = chooser(options)
            except Exception:  # noqa
                picked = None
            if picked is not None and any(Path(picked) == c for c in tied):
                best = Path(picked)
                if log:
                    log(f"Вы выбрали: {best.relative_to(folder)}")
                return best
        if log and len(cands) > 1:
            others = ", ".join(str(c.relative_to(folder)) for c in cands[1:5])
            log(f"Выбран: {best.relative_to(folder)} (подходящих exe: {len(cands)}). "
                f"Другие варианты: {others}. Если запустилось не то, укажите exe вручную.")
        return best
    return None


def log_exe_candidates(folder: Path, log, limit=30):
    """В лог: какие exe есть в папке и почему каждый отсеян (помогает выбрать вручную)."""
    exes = sorted(folder.rglob("*.exe"),
                  key=lambda p: (len(p.relative_to(folder).parts), str(p).lower()))
    if not exes:
        log(f"В папке {folder} вообще нет exe-файлов. Проверьте, что программа "
            "распаковалась или установилась именно сюда.")
        return
    log(f"Найдено exe: {len(exes)}. Вот первые {min(limit, len(exes))} и почему они не подошли:")
    for p in exes[:limit]:
        try:
            why = exe_reject_reason(p, folder)
            size = fmt_size(p.stat().st_size)
        except OSError:
            why, size = "не читается", "?"
        if why is None:
            note = "подходит" + (" (низкий приоритет)" if any(w in p.name.lower() for w in SOFT_PENALTY) else "")
        else:
            note = "отсеян: " + why
        log(f"  {p.relative_to(folder)} ({size}) - {note}")
    log("Скопируйте нужное имя в поле «Главный exe» и запустите режим «Только Launch.bat».")


def find_installer(folder: Path):
    """Ищет внутри распакованного архива установщик (exe Inno/NSIS/WiX, msi, msix)."""
    cands = []
    for p in folder.rglob("*"):
        try:
            if not p.is_file():
                continue
            parts = p.relative_to(folder).parts
            if len(parts) > 3 or any(j in p.name.lower() for j in INSTALLER_JUNK):
                continue
            suffix = p.suffix.lower()
            if suffix == ".msi" or suffix in MSIX_EXT:
                pass
            elif suffix == ".exe" and p.stat().st_size > 512 * 1024:
                if detect_type(p) not in ("inno", "nsis", "wix"):
                    continue
            else:
                continue
            low = p.name.lower()
            looks_like = any(w in low for w in ("setup", "install", "inst"))
            cands.append((not looks_like, len(parts), -p.stat().st_size, p))
        except OSError:
            continue
    if not cands:
        return None
    cands.sort(key=lambda c: c[:3])
    return cands[0][3]


def resolve_manual(app: Path, manual: str, log):
    """Главный exe, указанный вручную: полный путь внутри App, относительный путь или просто имя."""
    manual = (manual or "").strip().strip('"')
    if not manual:
        return None
    p = Path(manual)
    c = p if p.is_absolute() else app / p
    if c.is_file():
        try:
            c.resolve().relative_to(app.resolve())
            return c.resolve()
        except ValueError:
            log("Указанный exe лежит вне папки App - выберите файл внутри App.")
            return None
    hits = [x for x in app.rglob(p.name) if x.is_file()]
    if hits:
        return min(hits, key=lambda x: len(x.relative_to(app).parts)).resolve()
    log(f"Файл '{manual}' не найден в App.")
    return None


# ---------------------------------------------------------------- MSIX / APPX

def fix_percent_names(root: Path, log):
    """В пакетах MSIX имена файлов могут быть закодированы (Program%20Files). Декодируем."""
    renamed = 0
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for name in filenames + dirnames:
            if "%" not in name:
                continue
            new = unquote(name)
            if new == name or any(c in new for c in '<>:"|?*/\\'):
                continue
            src, dst = Path(dirpath) / name, Path(dirpath) / new
            if dst.exists():
                continue
            try:
                src.rename(dst)
                renamed += 1
            except OSError:
                pass
    if renamed:
        log(f"MSIX: исправлено имён с кодировкой %XX: {renamed}")


def pick_inner_package(app: Path):
    """Для бандла (.msixbundle / .appxbundle) выбирает основной пакет под x64."""
    is_bundle = ((app / "AppxBundleManifest.xml").is_file()
                 or (app / "AppxMetaData" / "AppxBundleManifest.xml").is_file())
    if not is_bundle:
        return None
    pk = [p for p in app.rglob("*")
          if p.is_file() and p.suffix.lower() in (".msix", ".appx")]
    if not pk:
        return None

    def score(p: Path):
        n = p.name.lower()
        return ("x64" in n or "amd64" in n, "x86" not in n and "arm" not in n,
                p.stat().st_size)
    return max(pk, key=score)


def msix_entry(app: Path, log):
    """Главный exe из AppxManifest.xml (Application/@Executable)."""
    mf = app / "AppxManifest.xml"
    if not mf.is_file():
        log("MSIX: AppxManifest.xml не найден - ищу exe обычным способом.")
        return None
    try:
        root = ET.parse(mf).getroot()
    except ET.ParseError as e:
        log(f"MSIX: не удалось прочитать манифест: {e}")
        return None
    execs, full_trust = [], False
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "Application" and el.get("Executable"):
            execs.append(el.get("Executable"))
        elif tag == "Capability" and el.get("Name") == "runFullTrust":
            full_trust = True
    if not full_trust:
        log("MSIX: в манифесте нет runFullTrust - это, скорее всего, UWP-приложение. "
            "Вне установленного пакета оно, вероятно, не запустится.")
    for rel in execs:
        if "$" in rel:          # шаблон вида $targetnametoken$.exe
            continue
        rel = rel.replace("\\", "/")
        cand = app / rel
        if cand.is_file() and cand.suffix.lower() == ".exe":
            return cand.resolve()
        hits = [x for x in app.rglob(Path(rel).name) if x.is_file()]
        if hits:
            return min(hits, key=lambda x: len(x.relative_to(app).parts)).resolve()
    return None


# chcp 65001 - чтобы cmd правильно читал пути с кириллицей из UTF-8 файла
DOTNET_RUNTIME_ARG = {"Microsoft.NETCore.App": "dotnet",
                      "Microsoft.WindowsDesktop.App": "windowsdesktop",
                      "Microsoft.AspNetCore.App": "aspnetcore"}


def needed_dotnet(exe: Path):
    """[(фреймворк, версия)] из <имя>.runtimeconfig.json рядом с exe (пусто, если файла нет)."""
    cfg = exe.with_name(exe.stem + ".runtimeconfig.json")
    try:
        data = json.loads(cfg.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    opts = data.get("runtimeOptions", {}) if isinstance(data, dict) else {}
    fws = list(opts.get("frameworks") or [])
    if opts.get("framework"):
        fws.append(opts["framework"])
    return [(fw["name"], str(fw.get("version", ""))) for fw in fws
            if isinstance(fw, dict) and fw.get("name")]


def dotnet_present(name: str, version: str, target: Path, program_files=None) -> bool:
    """Есть ли нужный рантайм (та же основная версия): в папке dotnet, DOTNET_ROOT или Program Files."""
    major = (version.split(".")[0] or "0") + "."
    roots = [Path(target) / "dotnet"]
    if os.environ.get("DOTNET_ROOT"):
        roots.append(Path(os.environ["DOTNET_ROOT"]))
    pf = program_files or os.environ.get("ProgramFiles")
    if pf:
        roots.append(Path(pf) / "dotnet")
    for r in roots:
        try:
            if any(x.name.startswith(major) for x in (r / "shared" / name).iterdir()):
                return True
        except OSError:
            pass
    return False


def dotnet_check(main: Path, target: Path, log, program_files=None):
    """Если программе нужен .NET, которого нет, создаёт Install_dotnet.bat/.ps1 и пишет подсказку."""
    missing = [(n, v) for n, v in needed_dotnet(main)
               if not dotnet_present(n, v, target, program_files)]
    if not missing:
        return []
    lines, seen = [], set()
    for name, version in missing:
        arg = DOTNET_RUNTIME_ARG.get(name)
        major = version.split(".")[0]
        if not arg or not major.isdigit() or (arg, major) in seen:
            continue
        seen.add((arg, major))
        lines.append(f"& .\\dotnet-install.ps1 -Runtime {arg} -Channel {major}.0 "
                     "-InstallDir (Join-Path $PSScriptRoot 'dotnet') -NoPath")
    if not lines:
        return missing
    ps = ("$ErrorActionPreference = 'Stop'\n"
          "Set-Location -LiteralPath $PSScriptRoot\n"
          "Invoke-WebRequest https://dot.net/v1/dotnet-install.ps1 -OutFile dotnet-install.ps1\n"
          + "\n".join(lines) + "\n"
          "Remove-Item dotnet-install.ps1\n")
    bat = ("@echo off\nchcp 65001 >nul\n"
           'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install_dotnet.ps1"\n'
           "echo.\npause\n")
    try:
        (Path(target) / "Install_dotnet.ps1").write_text(ps, encoding="utf-8")
        (Path(target) / "Install_dotnet.bat").write_text(bat, encoding="utf-8")
    except OSError as e:
        log(f"Не удалось создать Install_dotnet.bat: {e}")
        return missing
    need = ", ".join(f"{n} {v}" for n, v in missing)
    log(f"Нужен .NET ({need}) для {main.name}, а на этом компьютере его не нашлось. "
        "Запустите Install_dotnet.bat в папке результата: он скачает рантайм в папку dotnet "
        "внутри портативной копии (права администратора не нужны), Launch.bat подхватит его сам.")
    return missing


LAUNCHER = r"""@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "DATA=%ROOT%Data"
if not exist "%DATA%\AppData\Roaming" mkdir "%DATA%\AppData\Roaming"
if not exist "%DATA%\AppData\Local"   mkdir "%DATA%\AppData\Local"
if not exist "%DATA%\Documents"       mkdir "%DATA%\Documents"
if not exist "%DATA%\Temp"            mkdir "%DATA%\Temp"
set "USERPROFILE=%DATA%"
set "APPDATA=%DATA%\AppData\Roaming"
set "LOCALAPPDATA=%DATA%\AppData\Local"
set "TEMP=%DATA%\Temp"
set "TMP=%DATA%\Temp"
if exist "%ROOT%dotnet\dotnet.exe" set "DOTNET_ROOT=%ROOT%dotnet"
{invoker}start "" /D "%ROOT%App\{rel_dir}" "%ROOT%App\{rel_exe}" %*
endlocal
"""

INVOKER_LINE = 'rem exe requires admin: run without UAC prompt (RunAsInvoker)\r\nset "__COMPAT_LAYER=RunAsInvoker"\r\n'


RUN_POLICY = {"value": "auto"}      # auto | noadmin | admin (как запускать exe, которому нужен админ)
RUN_POLICIES = ("auto", "noadmin", "admin")


def analyze_exe(exe, limit=64 * 1024 * 1024) -> dict:
    """Быстрый статический разбор exe (файл не запускается).
    level: asInvoker / highestAvailable / requireAdministrator / None (манифеста нет);
    arch: x64 / x86 / arm64 / ?; dotnet: управляемый код (.NET); online_stub: маленькая
    заглушка, которая сама скачивает программу из сети; tags: найденные признаки упаковки."""
    res = {"level": None, "arch": "?", "dotnet": False, "online_stub": False, "tags": [],
           "urls": [], "size": 0}
    try:
        size = Path(exe).stat().st_size
        res["size"] = size
        data = b""
        with open(exe, "rb") as f:
            data = f.read(limit)
    except OSError:
        return res
    if data[:2] == b"MZ" and len(data) > 0x40:
        off = int.from_bytes(data[0x3C:0x40], "little")
        if data[off:off + 4] == b"PE\0\0":
            m = int.from_bytes(data[off + 4:off + 6], "little")
            res["arch"] = {0x8664: "x64", 0x14C: "x86", 0xAA64: "arm64"}.get(m, "?")
    for lvl in (b"requireAdministrator", b"highestAvailable", b"asInvoker"):
        if lvl in data:
            res["level"] = lvl.decode()
            break
    wide = data.replace(b"\x00", b"")        # грубо: UTF-16 без нулей, только для поиска слов
    res["dotnet"] = b"mscoree.dll" in data or b"mscoree.dll" in wide
    for tag, keys in (("InstallShield", (b"InstallShield",)), ("Burn/WiX", (b"WixBundle", b"WiX Burn")),
                      ("Inno", (b"Inno Setup",)), ("NSIS", (b"Nullsoft",)),
                      ("7z-SFX", (b"7zSFX", b"7-Zip SFX")), ("Electron", (b"electron.asar", b"Electron")),
                      ("PyInstaller", (b"PyInstaller", b"pyi-runtime")),
                      ("Themida/VMProtect", (b"Themida", b".themida", b"VMProtect", b".vmp0"))):
        if any(k in data or k in wide for k in keys):
            res["tags"].append(tag)
    strs = re.findall(rb"[\x20-\x7e]{6,}", data)                         # ASCII-строки
    strs += [m.replace(b"\x00", b"") for m in re.findall(rb"(?:[\x20-\x7e]\x00){6,}", data)]  # UTF-16
    urls = []
    for st in strs:
        for u in re.split(rb"(?=https?://)", st):
            if u.startswith(b"http"):
                urls.append(u[:200].decode("ascii", "ignore"))
    dl = sorted({u for u in urls if re.search(r"\.(exe|msi|zip|7z|rar|cab)(\?|$)", u, re.I)})
    res["urls"] = dl[:3]
    low = b"\n".join(strs).lower()
    hint = b"cdn base" in low or b"winhttp" in low or b"urldownloadtofile" in low
    # онлайн-заглушка: небольшой файл + ссылки на скачивание exe/архивов,
    # либо слова про загрузку и CDN без прямой ссылки
    res["online_stub"] = size < 16 * 1024 * 1024 and (bool(dl) or (b"download" in low and hint))
    return res


def requires_admin(exe) -> bool:
    return analyze_exe(exe)["level"] in ("requireAdministrator", "highestAvailable")


def exe_report(info_exe: dict, name: str, policy: str, log) -> bool:
    """Печатает в лог, что за exe и как он будет запускаться. Возвращает: нужен ли RunAsInvoker."""
    a = info_exe
    kind = []
    if a["dotnet"]:
        kind.append(".NET")
    if a["tags"]:
        kind.append("/".join(a["tags"]))
    log(f"Разбор {name}: {a['arch']}, {fmt_size(a['size'])}"
        + (f", {', '.join(kind)}" if kind else "")
        + f", манифест: {a['level'] or 'нет'}.")
    if a["online_stub"]:
        log("Это похоже на онлайн-заглушку: внутри ссылка на скачивание "
            f"({a['urls'][0] if a['urls'] else 'адрес скачивания найден по косвенным признакам'}). Сама программа скачается при запуске и встанет в систему, "
            "так что портативной копией это не станет. Для настоящей переносимости скачайте "
            "полный офлайн-установщик и сделайте портативным его.")
    if "Themida/VMProtect" in a["tags"]:
        log("Файл защищён упаковщиком: распаковать и проанализировать его нельзя, только запуск.")
    wants_admin = a["level"] in ("requireAdministrator", "highestAvailable")
    if policy == "admin":
        log("Запуск: с запросом UAC (выбрано вручную). Launch.bat не меняет права.")
        return False
    if policy == "noadmin":
        log("Запуск: без запроса UAC (RunAsInvoker, выбрано вручную).")
        return True
    if wants_admin:
        log(f"{name} просит права администратора. Launch.bat запускает его без запроса UAC "
            "(RunAsInvoker), пароль не нужен. Если программа реально пишет в Program Files, "
            "HKLM, ставит службы или драйверы, без прав она может не заработать. Тогда "
            "используйте Launch_admin.bat (обычный запуск с запросом UAC).")
        return True
    log("Запуск: обычный, повышение прав не требуется.")
    return False


def unreal_shipping(stub: Path):
    """...-Shipping.exe игры на Unreal Engine для корневого exe (предпочитаем Win64)."""
    try:
        found = sorted((stub.parent / stub.stem / "Binaries").glob("*/*-Shipping.exe"),
                       key=lambda p: (p.parent.name.lower() != "win64", str(p).lower()))
    except OSError:
        return None
    return found[0] if found else None


def dx_missing(dest: Path, system_root=None) -> bool:
    """True, если xinput1_3.dll (DirectX June 2010) нет ни в системе, ни рядом с игрой."""
    root = system_root or os.environ.get("SystemRoot") or ""
    if root and (Path(root) / "System32" / "xinput1_3.dll").is_file():
        return False
    return not (Path(dest) / "xinput1_3.dll").is_file()


# ---------------------------------------------------- встроенные библиотеки DirectX (app-local)

DX_NAMES = ("xinput1_3", "x3daudio1_7", "xapofx1_5", "xaudio2_7", "xaudio2_6", "xapofx1_4",
            "x3daudio1_6", "d3dx9_43", "d3dx10_43", "d3dx11_43", "d3dcompiler_43", "d3dcsx_43",
            "xactengine3_7",
            # старые выпуски DirectX (2005-2009) для старых игр, только x86
            "d3dcompiler_33", "d3dcompiler_34", "d3dcompiler_35", "d3dcompiler_36",
            "d3dcompiler_37", "d3dcompiler_38", "d3dcompiler_39", "d3dcompiler_40",
            "d3dcompiler_41", "d3dcompiler_42", "d3dx10", "d3dx10_33", "d3dx10_34", "d3dx10_35",
            "d3dx10_36", "d3dx10_37", "d3dx10_38", "d3dx10_39", "d3dx10_40", "d3dx10_41",
            "d3dx10_42", "d3dx11_42", "d3dx9_24", "d3dx9_25", "d3dx9_26", "d3dx9_27", "d3dx9_28",
            "d3dx9_29", "d3dx9_30", "d3dx9_31", "d3dx9_32", "d3dx9_33", "d3dx9_34", "d3dx9_35",
            "d3dx9_36", "d3dx9_37", "d3dx9_38", "d3dx9_39", "d3dx9_40", "d3dx9_41", "d3dx9_42",
            "x3daudio1_0", "x3daudio1_1", "x3daudio1_2", "x3daudio1_3", "x3daudio1_4",
            "x3daudio1_5", "xactengine2_0", "xactengine2_1", "xactengine2_10", "xactengine2_2",
            "xactengine2_3", "xactengine2_4", "xactengine2_5", "xactengine2_6", "xactengine2_7",
            "xactengine2_8", "xactengine2_9", "xactengine3_0", "xactengine3_1", "xactengine3_2",
            "xactengine3_3", "xactengine3_4", "xactengine3_5", "xactengine3_6", "xapofx1_0",
            "xapofx1_1", "xapofx1_2", "xapofx1_3", "xaudio2_0", "xaudio2_1", "xaudio2_2",
            "xaudio2_3", "xaudio2_4", "xaudio2_5", "xinput1_1", "xinput1_2", "xinput9_1_0")
DX_UE_DEFAULT = ("xinput1_3", "x3daudio1_7", "xapofx1_5", "xaudio2_7")   # то, что просят игры на UE4

# Остальные встроенные библиотеки: те же cab-наборы в папке dx (имя cab содержит x86 или x64).
# Набор собирает tools/collect_redist.py из DLL, которые уже стоят на компьютере разработчика.
RUNTIME_FAMILIES = (
    ("DirectX", DX_NAMES),
    ("Visual C++ 2015-2022", ("vcruntime140", "vcruntime140_1", "msvcp140", "msvcp140_1",
                              "msvcp140_2", "msvcp140_atomic_wait", "msvcp140_codecvt_ids",
                              "concrt140", "vcomp140")),
    ("Visual C++ 2013", ("msvcr120", "msvcp120", "vcomp120")),
    ("Visual C++ 2012", ("msvcr110", "msvcp110", "vcomp110")),
    ("Visual C++ 2010", ("msvcr100", "msvcp100", "vcomp100")),
    ("OpenAL", ("openal32",)),
)
RUNTIME_NAMES = tuple(n for _, names in RUNTIME_FAMILIES for n in names)


# Библиотеки, которые нужно положить вместе с основной (OpenAL32.dll сам по себе ищет wrap_oal.dll).
RUNTIME_COMPANIONS = {"openal32": ("wrap_oal",)}


def runtime_family(name: str) -> str:
    """К какому набору относится библиотека (имя без .dll, в любом регистре)."""
    low = name.lower()
    return next((fam for fam, names in RUNTIME_FAMILIES if low in names), "")


def dx_dir() -> Path:
    base = getattr(sys, "_MEIPASS", None)
    return (Path(base) if base else Path(__file__).resolve().parent) / "dx"


def cab_read(path):
    """Читает cab. Возвращает (список (имя, смещение, размер, папка), данные папок или None).
    Данные читаем для cab без сжатия и MSZIP (так устроены cab из DirectX); для остальных None."""
    d = Path(path).read_bytes()
    if d[:4] != b"MSCF":
        raise ValueError("не cab")
    coff_files = struct.unpack("<I", d[16:20])[0]
    nfold, nfiles, flags = struct.unpack("<HHH", d[26:32])
    pos, cb_cab, cb_fold, cb_data = 36, 0, 0, 0
    if flags & 4:
        cb_cab, cb_fold, cb_data = struct.unpack("<HBB", d[36:40])
        pos = 40 + cb_cab
    if flags & 3:                       # цепочка из нескольких cab: не поддерживаем
        raise ValueError("многотомный cab")
    folders = []
    for _ in range(nfold):
        off, nblk, comp = struct.unpack("<IHH", d[pos:pos + 8])
        folders.append((off, nblk, comp & 0xF))
        pos += 8 + cb_fold
    files, p = [], coff_files
    for _ in range(nfiles):
        size, uoff, fi = struct.unpack("<IIH", d[p:p + 10])
        e = d.index(b"\0", p + 16)
        files.append((d[p + 16:e].decode("utf-8", "replace"), uoff, size, fi))
        p = e + 1
    datas = []
    for off, nblk, comp in folders:
        if comp not in (0, 1):          # 0 - без сжатия, 1 - MSZIP; LZX и прочее: через expand.exe
            datas.append(None)
            continue
        try:
            out, q, prev = [], off, b""
            for _ in range(nblk):
                cb, cu = struct.unpack("<HH", d[q + 4:q + 8])
                q += 8 + cb_data
                blk = d[q:q + cb]
                q += cb
                if comp == 1:
                    if blk[:2] != b"CK":
                        raise ValueError("битый блок MSZIP")
                    dec = zlib.decompressobj(-15, zdict=prev[-32768:]) if prev else zlib.decompressobj(-15)
                    blk = dec.decompress(blk[2:])
                    if len(blk) != cu:
                        raise ValueError("битый блок MSZIP")
                    prev = blk
                out.append(blk)
            datas.append(b"".join(out))
        except (ValueError, zlib.error, struct.error):
            datas.append(None)          # папка не читается нашим кодом: имена файлов остаются, распаковку возьмёт expand.exe
    return files, datas


def dx_index(folder=None) -> dict:
    """{(arch, имя_dll_в_нижнем_регистре): путь_к_cab} по всем cab из папки dx."""
    idx = {}
    d = Path(folder) if folder else dx_dir()
    if not d.is_dir():
        return idx
    for cab in sorted(d.glob("*.cab")):
        low = cab.name.lower()
        arch = "x64" if "x64" in low else "x86" if "x86" in low else None
        if not arch:
            continue
        try:
            files, _ = cab_read(cab)
        except (OSError, ValueError, struct.error):
            continue
        for name, *_ in files:
            if name.lower().endswith(".dll"):
                idx.setdefault((arch, name.lower()), cab)
    return idx


def _has_expand() -> bool:
    return os.name == "nt"


def dx_extract(cab, wanted, dest: Path, log=None) -> list:
    """Кладёт нужные dll из cab в dest. Без сжатия и MSZIP читаем сами, остальное (LZX)
    отдаём expand.exe: он есть в любой Windows и не требует прав администратора."""
    dest = Path(dest)
    done = []
    files, datas = cab_read(cab)
    names = [n for n, *_ in files if n.lower() in wanted]
    for name, uoff, size, fi in files:
        if name.lower() in wanted and fi < len(datas) and datas[fi] is not None:
            (dest / name).write_bytes(datas[fi][uoff:uoff + size])
            done.append(name)
    for n in (x for x in names if x not in done):
        if not _has_expand():
            if log:
                log(f"{n}: в этом cab сжатие LZX, распаковать можно только на Windows (expand.exe).")
            continue
        r = subprocess.run(["expand.exe", str(cab), f"-F:{n}", str(dest)], capture_output=True,
                           text=True, stdin=subprocess.DEVNULL,
                           creationflags=0x08000000 if os.name == "nt" else 0)   # без окна консоли
        if (dest / n).is_file():
            done.append(n)
        elif log:
            log(f"expand.exe не смог достать {n}: {(r.stdout or r.stderr).strip()[:200]}")
    return done


def scan_dx_names(exe, limit=700 * 1024 * 1024) -> set:
    """Какие встроенные библиотеки (DirectX, Visual C++, OpenAL: RUNTIME_NAMES) упомянуты в exe
    (ASCII или UTF-16), по кускам."""
    pats = {}
    for n in RUNTIME_NAMES:
        a = (n + ".dll").encode()
        pats[n] = (a, b"\x00".join(bytes([c]) for c in a))
    found, tail, done = set(), b"", 0
    try:
        with open(exe, "rb") as f:
            while done < limit:
                chunk = f.read(16 * 1024 * 1024)
                if not chunk:
                    break
                blob = (tail + chunk).lower()
                for n, (a, w) in pats.items():
                    if n not in found and (a in blob or w in blob):
                        found.add(n)
                tail, done = chunk[-64:], done + len(chunk)
    except OSError:
        pass
    return found


def dx_plan(launch: Path, system_root=None, index=None) -> dict:
    """Какие встроенные библиотеки (DirectX, Visual C++, OpenAL) нужны exe, но отсутствуют
    и в системе, и рядом с ним."""
    arch = analyze_exe(launch)["arch"]
    arch = "x86" if arch == "x86" else "x64"
    need = scan_dx_names(launch)
    if unreal_rank(launch):
        need |= set(DX_UE_DEFAULT)
    root = system_root or os.environ.get("SystemRoot") or ""
    sysdirs = []
    if root:
        sysdirs = [Path(root) / ("SysWOW64" if arch == "x86" and (Path(root) / "SysWOW64").is_dir()
                                 else "System32")]
    missing = sorted(n for n in need
                     if not any((d / (n + ".dll")).is_file() for d in sysdirs)
                     and not (launch.parent / (n + ".dll")).is_file())
    idx = dx_index() if index is None else index
    return {"arch": arch, "missing": missing,
            "bundled": [n for n in missing if (arch, n + ".dll") in idx],
            "absent": [n for n in missing if (arch, n + ".dll") not in idx], "index": idx}


def runtime_groups(names) -> list:
    """[(набор, [имена.dll])] в порядке RUNTIME_FAMILIES; незнакомые имена идут в конец."""
    by = {}
    for n in names:
        by.setdefault(runtime_family(n) or "Прочее", []).append(n + ".dll")
    order = [f for f, _ in RUNTIME_FAMILIES] + ["Прочее"]
    return [(f, by[f]) for f in order if f in by]


def dx_question(plan: dict) -> str:
    lines = "\n".join(f"  {fam}: {', '.join(files)}" for fam, files in runtime_groups(plan["missing"]))
    t = (tr("Программе нужны библиотеки, которых нет в системе:\n{0}\n\nПоложить их в папку программы? Права администратора не нужны, система не меняется, всё остаётся внутри портативной папки.\n\nДа - положить.\nНет - продолжить без них (программа может не запуститься).\nОтмена - прервать.", lines))
    if plan["absent"]:
        t += (tr("\n\nЧасть файлов в Portabilizer не встроена: ")
              + ", ".join(n + ".dll" for n in plan["absent"]))
        if any(n in DX_NAMES for n in plan["absent"]):
            t += tr(". Для DirectX будет создан DX_fix.bat (скачает полный пакет DirectX).")
        else:
            t += tr(". Их придётся поставить вручную.")
    return t


DX_URL = ("https://download.microsoft.com/download/8/4/A/"
          "84A35BF1-DAFE-4AE8-82AF-AD2AE20B6B14/directx_Jun2010_redist.exe")
DX_PAGE = "https://www.microsoft.com/en-us/download/details.aspx?id=8109"

# DX_fix.bat: библиотеки DirectX (June 2010) рядом с игрой, без прав администратора.
# Ключ /Q /T: тихой распаковки не подтверждён документацией: после него проверяем результат,
# а при неудаче показываем ручную инструкцию (так же, как в успешном ручном способе).
DX_FIX = r"""@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "DEST=%ROOT%@DEST@"
set "DX=%ROOT%DX9"
echo Этот файл кладёт библиотеки DirectX (June 2010) рядом с игрой.
echo Права администратора не нужны, система не изменяется.
echo.
if exist "%DX%\*x64.cab" goto extract
echo Скачиваю DirectX End-User Runtimes (June 2010), около 96 МБ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '@URL@' -OutFile '%ROOT%directx_Jun2010_redist.exe' } catch { Write-Host $_.Exception.Message }"
if exist "%ROOT%directx_Jun2010_redist.exe" (
  echo Распаковываю пакет ^(в систему ничего не ставится^)...
  "%ROOT%directx_Jun2010_redist.exe" /Q /T:"%DX%"
)
if exist "%DX%\*x64.cab" goto extract
echo.
echo Автоматически не получилось. Сделайте вручную:
echo   1. Скачайте directx_Jun2010_redist.exe: @PAGE@
echo   2. Запустите его и в качестве папки распаковки укажите:
echo      %DX%
echo      Файл DXSETUP.exe из неё запускать не нужно.
echo   3. Запустите DX_fix.bat ещё раз.
pause
exit /b 1
:extract
pushd "%DX%"
md Files\x64 2>nul
expand.exe *x64.cab -F:*.dll .\Files\x64 -R
popd
copy /Y "%DX%\Files\x64\*.dll" "%DEST%\" >nul
if errorlevel 1 goto fail
echo.
echo Готово: библиотеки скопированы в
echo   %DEST%
echo Папку DX9 и файл directx_Jun2010_redist.exe теперь можно удалить.
pause
exit /b 0
:fail
echo Не удалось скопировать файлы в %DEST%
pause
exit /b 1
"""


# ---------------------------------------------------------------- ярлык на рабочем столе
# Create_Shortcut.bat лежит в папке результата: создаёт на рабочем столе ярлык на Launch.bat с иконкой
# программы. Пути считаются от места самого файла, поэтому после переноса папки его достаточно запустить
# снова (старый ярлык с тем же именем будет заменён). Права администратора не нужны.
SHORTCUT_BAT = r"""@echo off
chcp 65001 >nul
setlocal
rem Creates a desktop shortcut to Launch.bat of this folder. Run again after moving the folder.
set "ROOT=%~dp0"
set "PZ_NAME=@NAME@"
set "PZ_ICON=@ICON@"
set "PZ_IDX=@IDX@"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $r=$env:ROOT.TrimEnd('\'); $d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d ($env:PZ_NAME+'.lnk'))); $s.TargetPath=Join-Path $r 'Launch.bat'; $s.WorkingDirectory=$r; $s.WindowStyle=7; if ($env:PZ_ICON) { $s.IconLocation=(Join-Path $r $env:PZ_ICON)+','+$env:PZ_IDX }; $s.Save()"
set "RC=%errorlevel%"
if /i "%~1"=="silent" exit /b %RC%
if not "%RC%"=="0" (
  echo Could not create the shortcut.
  pause
  exit /b %RC%
)
echo Done: the shortcut "%PZ_NAME%" is on the desktop.
timeout /t 3 >nul
exit /b 0
"""


def shortcut_name(target) -> str:
    """Имя ярлыка: имя папки результата без хвоста _portable и без символов, недопустимых в имени файла."""
    name = re.sub(r"(?i)[ _-]*portable$", "", Path(target).name).strip()
    name = re.sub(r'[<>:"/\\|?*%\x00-\x1f]', "", name).strip(" .")
    return name or "Portabilizer"


def pe_has_icon(path):
    """True/False: есть ли в exe/dll ресурс иконки (RT_GROUP_ICON). None - файл не удалось разобрать
    (тогда считаем, что иконка может быть: Windows сама покажет стандартную, если её нет)."""
    try:
        with open(path, "rb") as f:
            d = f.read(1 << 20)
            if d[:2] != b"MZ":
                return None
            pe = struct.unpack_from("<I", d, 0x3C)[0]
            if d[pe:pe + 4] != b"PE\0\0":
                return None
            nsec, osz = struct.unpack_from("<H", d, pe + 6)[0], struct.unpack_from("<H", d, pe + 20)[0]
            opt = pe + 24
            magic = struct.unpack_from("<H", d, opt)[0]
            dd = opt + (112 if magic == 0x20B else 96)
            rva, size = struct.unpack_from("<II", d, dd + 2 * 8)
            if not rva or not size:
                return False
            for i in range(nsec):
                o = opt + osz + i * 40
                vsize, va, rsize, raw = struct.unpack_from("<IIII", d, o + 8)
                if va <= rva < va + max(vsize, rsize):
                    off = raw + rva - va
                    f.seek(off)
                    head = f.read(16)
                    named, ids = struct.unpack_from("<HH", head, 12)
                    ent = f.read(8 * (named + ids))
                    for k in range(named, named + ids):
                        if struct.unpack_from("<I", ent, k * 8)[0] == 14:
                            return True
                    return False
    except (OSError, struct.error):
        return None
    return None


def autorun_icon(folder: Path):
    """Из autorun.inf: (относительный путь, номер) иконки диска или None."""
    for name in ("autorun.inf", "AUTORUN.INF", "Autorun.inf"):
        f = Path(folder) / name
        if f.is_file():
            try:
                text = f.read_bytes().decode("utf-8", "replace")
            except OSError:
                return None
            m = re.search(r"(?im)^\s*icon\s*=\s*\"?([^\r\n\",]+?)\"?\s*(?:,\s*(-?\d+))?\s*$", text)
            if m:
                return m.group(1).strip().strip("\\/"), int(m.group(2) or 0)
    return None


def pick_icon(app: Path, main: Path):
    """Откуда взять иконку ярлыка: (путь относительно папки результата, номер) или None.
    Порядок: сам главный exe (если в нём есть иконка), .ico рядом с ним, иконка из autorun.inf диска."""
    app, main = Path(app), Path(main)

    def rel(p):
        return "App\\" + str(Path(p).relative_to(app)).replace("/", "\\")
    try:
        if main.is_file() and pe_has_icon(main) is not False:
            return rel(main), 0
        icos = []
        for d in (main.parent, app):
            icos += [p for p in sorted(d.glob("*.ico")) if p not in icos]
        if icos:
            same = [p for p in icos if p.stem.lower() == main.stem.lower()]
            return rel((same or icos)[0]), 0
        ar = autorun_icon(app)
        if ar and (app / ar[0]).is_file():
            return rel(app / ar[0]), ar[1]
    except (OSError, ValueError):
        pass
    return None


def write_shortcut_script(target: Path, app: Path, main: Path, name=None):
    """Пишет Create_Shortcut.bat в папку результата. Возвращает (путь к файлу, имя ярлыка, иконка или None)."""
    name = name or shortcut_name(target)
    icon = pick_icon(app, main)
    bat = Path(target) / "Create_Shortcut.bat"
    esc = lambda v: str(v).replace("%", "%%")                                   # noqa: E731
    bat.write_text(SHORTCUT_BAT.replace("\r\n", "\n")
                   .replace("@NAME@", esc(name)).replace("@ICON@", esc(icon[0]) if icon else "")
                   .replace("@IDX@", str(icon[1]) if icon else "0"), encoding="utf-8")
    return bat, name, icon


def create_desktop_shortcut(bat: Path, log) -> bool:
    """Запускает Create_Shortcut.bat без окна. Только Windows."""
    if os.name != "nt":
        log("Ярлык на рабочем столе создаётся только в Windows.")
        return False
    try:
        r = subprocess.run(["cmd", "/c", str(bat), "silent"], capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as e:
        log(f"Ярлык не создан: {e}")
        return False
    if r.returncode != 0:
        log("Ярлык не создан (PowerShell вернул ошибку). Запустите Create_Shortcut.bat в папке результата.")
        return False
    return True


def finish(target: Path, app: Path, main: Path, log, info=None, direct_unreal=True,
           system_root=None) -> bool:
    """Пишет Launch.bat. Для игр на Unreal Engine запускает ...-Shipping.exe напрямую
    (если exe не выбран вручную) и при необходимости создаёт DX_fix.bat."""
    launch, stub = main, None
    if direct_unreal and unreal_rank(main) == 2:
        shipping = unreal_shipping(main)
        if shipping:
            launch, stub = shipping, main
    base = app.resolve()

    def write_launcher(name, exe_rel, invoker=False):
        d = exe_rel.parent
        (target / name).write_text(
            LAUNCHER.format(rel_exe=str(exe_rel).replace("/", "\\"),
                            rel_dir=str(d).replace("/", "\\") if str(d) != "." else "",
                            invoker=INVOKER_LINE.replace("\r\n", "\n") if invoker else ""),
            encoding="utf-8")

    rel_exe = launch.relative_to(base)
    policy = RUN_POLICY["value"] if RUN_POLICY["value"] in RUN_POLICIES else "auto"
    needs_admin = exe_report(analyze_exe(launch), launch.name, policy, log)
    write_launcher("Launch.bat", rel_exe, invoker=needs_admin)
    if needs_admin or policy == "admin":
        write_launcher("Launch_admin.bat", rel_exe)
    (target / "Data").mkdir(exist_ok=True)
    notes = info.setdefault("notes", []) if info is not None else []
    if info is not None:
        info["main"] = str(rel_exe)
    if stub is not None:
        write_launcher("Launch_stub.bat", stub.relative_to(base))
        log(f"Игра на Unreal Engine: Launch.bat запускает {launch.name} напрямую. Корневой "
            f"{stub.name} при первом запуске просит поставить DirectX и Visual C++ в систему и "
            "закрывается, если отказаться. Запуск через него: Launch_stub.bat.")
        notes.append(f"Unreal: запуск {launch.name}")
    plan = dx_plan(launch, system_root)
    if plan["missing"]:
        prompt = (info or {}).get("dx_prompt")
        choice = prompt(dx_question(plan)) if prompt else "install"
        names = ", ".join(n + ".dll" for n in plan["missing"])
        if choice == "cancel":
            log("Отменено: нужны библиотеки (" + names + ").")
            raise JobCancelled()
        put = []
        if choice == "install":
            wanted = {n + ".dll" for n in plan["bundled"]}
            wanted |= {c + ".dll" for n in plan["bundled"] for c in RUNTIME_COMPANIONS.get(n, ())}
            for cab in sorted({plan["index"][(plan["arch"], n + ".dll")] for n in plan["bundled"]}):
                put += dx_extract(cab, wanted, launch.parent, log)
            if put:
                log(f"Библиотеки ({plan['arch']}) положены рядом с {launch.name}: "
                    f"{', '.join(sorted(put))}.")
                notes.append("Библиотеки: " + ", ".join(sorted(put)))
        put_low = {x.lower() for x in put}
        left = [n for n in plan["missing"] if n + ".dll" not in put_low]
        left_dx = [n for n in left if n in DX_NAMES]
        left_other = [n for n in left if n not in DX_NAMES]
        if left_dx:
            dest = str(launch.parent.resolve().relative_to(target.resolve())).replace("/", "\\")
            (target / "DX_fix.bat").write_text(
                DX_FIX.replace("@DEST@", dest).replace("@URL@", DX_URL).replace("@PAGE@", DX_PAGE),
                encoding="utf-8")
            log(("Без DirectX выбрано продолжить. " if choice != "install" else "")
                + "Не хватает: " + ", ".join(n + ".dll" for n in left_dx)
                + ". Если программа пожалуется на них, запустите DX_fix.bat в папке результата "
                "(права администратора не нужны).")
            notes.append("нужен DX_fix.bat")
        if left_other:
            fams = ", ".join(f for f, _ in runtime_groups(left_other))
            log(("Выбрано продолжить без них. " if choice != "install" else "")
                + "Не хватает: " + ", ".join(n + ".dll" for n in left_other)
                + f" ({fams}). В Portabilizer они не встроены или не подошли по разрядности: "
                "если программа пожалуется, поставьте соответствующий пакет в систему.")
            notes.append("не хватает: " + ", ".join(n + ".dll" for n in left_other))
    if needs_admin:
        notes.append("exe требует админа: Launch.bat идёт через RunAsInvoker")
    dotnet_check(main, target, log)
    try:
        bat, sc_name, icon = write_shortcut_script(target, app, main)
        if info is not None:
            info["shortcut"] = {"bat": str(bat), "name": sc_name, "icon": icon[0] if icon else ""}
        ask = (info or {}).get("shortcut_prompt")
        if ask and ask(sc_name, bool(icon)):
            if create_desktop_shortcut(bat, log):
                log(f"Ярлык «{sc_name}» создан на рабочем столе.")
                notes.append("ярлык на рабочем столе")
        elif not icon:
            log("Иконку для ярлыка найти не удалось: ярлык будет со стандартной.")
    except (OSError, ValueError) as e:
        log(f"Create_Shortcut.bat не создан: {e}")
    log(f"Готово: {target}")
    log(f"Главный exe: {rel_exe}")
    log("Запускайте через Launch.bat. Папку можно переносить на флешку.")
    return True


# ---------------------------------------------------------------- радикальный режим (R)

EXTRACT_WARNINGS = []       # предупреждения распаковщика за текущую задачу (код 1 у 7-Zip)


def _rmtree(path: Path):
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=lambda func, p, exc: _force_remove(func, p))
    else:
        shutil.rmtree(path, onerror=lambda func, p, exc: _force_remove(func, p))


def same_drive(a, b) -> bool:
    """Лежат ли пути на одном диске/разделе (тогда перенос - мгновенное переименование)."""
    try:
        pa, pb = existing_parent(Path(a).resolve()), existing_parent(Path(b).resolve())
        if os.name == "nt":
            return pa.drive.lower() == pb.drive.lower()
        return os.stat(pa).st_dev == os.stat(pb).st_dev
    except OSError:
        return False


def radical_cleanup(exe: Path, target: Path, info, log, job=None) -> dict:
    """Радикальный режим: удаляет исходный файл (и тома архива) и временные копии
    Extracted*, но только после проверенного успеха. При малейшем сомнении ничего не трогает."""
    res = {"deleted": [], "freed": 0, "kept_reason": "", "moved": False}
    app = Path(target) / "App"
    if info.get("moved_source"):             # исходник уже перенесён в App: удалять нечего, копии не было
        res["moved"] = True
        try:
            res["freed"] = (app / Path(info["moved_source"]).name).stat().st_size
        except OSError:
            pass
        log("Радикальный режим: исходный файл перенесён, а не скопирован - лишних гигабайт не занято.")

    def keep(reason):
        res["kept_reason"] = reason
        log("Исходный файл НЕ удалён: " + reason + ".")
        return res

    if job is not None and job.cancelled:
        return keep("работа была прервана")
    if not (Path(target) / "Launch.bat").is_file():
        return keep("Launch.bat не создан")
    if not app.is_dir() or not any(app.iterdir()):
        return keep("папка App пуста")
    if EXTRACT_WARNINGS:
        return keep("распаковщик сообщил о предупреждениях (" + EXTRACT_WARNINGS[0] + ")")
    expected = info.get("expected_total")
    if expected and not info.get("chained"):
        got = dir_size(app)
        if got < expected * 0.98:
            return keep(f"распаковано {fmt_size(got)} из {fmt_size(expected)}")
    files = [f for f in source_group(Path(exe)) if f.is_file()]
    if info.get("moved_source"):
        files = []
    tr = Path(target).resolve()
    for f in files:
        fr = f.resolve()
        if fr == tr or tr in fr.parents:
            return keep("исходный файл лежит внутри папки результата")
    for f in files:
        try:
            size = f.stat().st_size
            f.unlink()
            res["deleted"].append(str(f))
            res["freed"] += size
            log(f"Удалён исходный файл: {f.name} ({fmt_size(size)})")
        except OSError as e:
            log(f"Не удалось удалить {f}: {e}")
    for name in ("Extracted_archive", "Extracted_bundle", "Extracted"):
        d = Path(target) / name
        if d.is_dir():
            size = dir_size(d)
            _rmtree(d)
            if not d.exists():
                res["deleted"].append(str(d))
                res["freed"] += size
                log(f"Удалена временная копия: {name} ({fmt_size(size)})")
    if info.get("bins"):
        log("Файлы .bin рядом с установщиком не удалялись (они могли понадобиться другим "
            "программам): " + ", ".join(Path(b).name for b in info["bins"]) +
            ". Если это данные того же репака, удалите их сами.")
    log(f"Радикальный режим: освобождено {fmt_size(res['freed'])}.")
    return res


def report_location(target: Path, app: Path, log):
    """Сообщает, где реально лежат файлы (App, Extracted и т.п.)."""
    shown = False
    if app.is_dir() and any(app.iterdir()):
        log(f"Файлы лежат в: {app}")
        shown = True
    for name in ("Extracted", "Extracted_archive", "Extracted_bundle"):
        d = target / name
        if d.is_dir() and any(d.iterdir()):
            log(f"Сохранено в: {d}")
            shown = True
    if not shown:
        log("Папки с файлами пусты.")


# ------------------------------------------------------------ основная логика

def _portabilize(exe_path, out_root, log, mode, manual_exe, target_override, job, info):
    if mode not in MODES:
        log(f"Неизвестный режим: {mode}")
        return False
    if not str(exe_path).strip():
        log("Не указан файл.")
        return False
    exe = Path(exe_path)
    target = target_override or (Path(out_root).resolve() / f"{clean_stem(exe)}_portable")
    app = target / "App"
    log(f"Режим: {mode}")

    # --- только Launch.bat для уже готовой папки ---
    if mode == "launcher":
        if not app.is_dir():
            log(f"Нет папки {app}. Сначала сделайте распаковку или установку.")
            return False
        main = resolve_manual(app, manual_exe, log) or find_main_exe(app, log, info.get('chooser'))
        if not main:
            log("Главный exe не найден - укажите его в поле 'Главный exe'.")
            log_exe_candidates(app, log)
            return False
        return finish(target, app, main, log, info, direct_unreal=not (manual_exe or "").strip())

    if not exe.is_file():
        log("Файл не найден.")
        return False
    if target.exists() and target_override is None:
        log(f"Папка уже есть: {target}")
        log("Удалите её, либо выберите режим 'Только Launch.bat'.")
        return False

    if target_override is None:
        # создаём папку сразу и ставим метку: по ней история и удаление узнают «свою» папку
        target.mkdir(parents=True, exist_ok=True)
        try:
            (target / MARKER).write_text(json.dumps(
                {"tool": "Portabilizer v8.9", "source": str(exe), "created": now_iso()},
                ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        info["set_target"](str(target))
        info["target"] = str(target)

    kind = detect_type(exe)
    info["kind"] = f"{info['kind']} > {kind}" if info.get("kind") else kind
    log(f"Тип: {kind}")
    main = None

    if kind == "plain":
        app.mkdir(parents=True, exist_ok=True)
        if info.get("radical"):
            # R: переносим, а не копируем - второй экземпляр на диске не появляется
            dest = app / exe.name
            try:
                if same_drive(exe, app):
                    os.replace(exe, dest)
                else:
                    shutil.move(str(exe), str(dest))   # между дисками: копия + удаление, пик = размер файла
                info["moved_source"] = str(exe)
                log(f"Режим R: файл перенесён в App без копии ({fmt_size(dest.stat().st_size)}).")
            except OSError as e:
                log(f"Не удалось перенести файл ({e}), копирую как обычно.")
                shutil.copy2(exe, dest)
        else:
            shutil.copy2(exe, app / exe.name)
            log("Это обычный exe - копирую как есть.")
        main = (app / exe.name).resolve()

    elif kind == "msix":
        if mode == "install":
            log("Режим установки не применим к MSIX/APPX: пакет только распаковывается.")
            return False
        if not extract(exe, kind, app, log, job):
            log("Не удалось распаковать пакет.")
            return False
        fix_percent_names(app, log)
        inner = pick_inner_package(app)
        if inner:
            rel = inner.relative_to(app)
            bundle = target / "Extracted_bundle"
            log(f"Это бандл. Основной пакет: {rel}. Распаковка бандла сохранена в {bundle}.")
            try:
                app.rename(bundle)
            except OSError as e:
                log(f"Не удалось переместить бандл: {e}")
                return False
            if not extract(bundle / rel, kind, app, log, job):
                log("Не удалось распаковать вложенный пакет.")
                return False
            fix_percent_names(app, log)
        main = resolve_manual(app, manual_exe, log) or msix_entry(app, log) or find_main_exe(app, log, info.get('chooser'))
        log("Внимание: MSIX распакован как обычная папка, без регистрации пакета. "
            "Классические (full trust) программы так обычно работают, "
            "а UWP-приложения и всё, что требует идентификатор пакета, могут не запуститься.")

    elif kind == "archive":
        if mode == "install":
            log("Режим установки не применим к архиву: он только распаковывается.")
            return False
        if info.get("radical"):
            info["expected_total"] = archive_unpacked_size(exe)   # для проверки полноты перед удалением
        if not extract(exe, kind, app, log, job):
            log("Не удалось распаковать архив.")
            return False
        main = resolve_manual(app, manual_exe, log) or find_main_exe(app, log, info.get('chooser'))
        if not main:
            inner = find_installer(app)
            if inner:
                rel = inner.relative_to(app)
                staging = target / "Extracted_archive"
                log(f"В архиве нет готовой программы, но есть установщик: {rel}. "
                    f"Продолжаю с ним. Содержимое архива сохранено в {staging}.")
                try:
                    app.rename(staging)
                except OSError as e:
                    log(f"Не удалось переместить распакованный архив: {e}")
                    return False
                info["chained"] = True
                ok = _portabilize(staging / rel, out_root, log, mode, manual_exe,
                                  target, job, info)
                if ok:
                    log(f"Папку {staging.name} можно удалить после проверки: "
                        "она нужна только как источник установщика.")
                return ok

    else:
        can_install = kind in ("inno", "nsis") and os.name == "nt"
        # .bin ищем только рядом с Inno/NSIS: у остальных типов они не имеют отношения к установке
        bins = sorted(exe.parent.glob("*.bin")) if kind in ("inno", "nsis") else []
        bin_size = sum(b.stat().st_size for b in bins)
        if mode == "install" and not can_install:
            log("Режим установки доступен только для Inno/NSIS установщиков в Windows.")
            return False
        info["bins"] = [str(b) for b in bins]
        if bins:
            log(f"Рядом с установщиком найдено .bin файлов: {len(bins)} "
                f"({fmt_size(bin_size)}): " + ", ".join(b.name for b in bins))

        do_install = mode == "install"
        do_extract = mode in ("extract", "auto")

        if do_extract:
            if not extract(exe, kind, app, log, job):
                log("Не удалось распаковать. Возможно, установщик нестандартный "
                    "(тогда нужен виртуализатор вроде Cameyo / Turbo Studio).")
                return False
            main = resolve_manual(app, manual_exe, log) or find_main_exe(app, log, info.get('chooser'))

            if mode == "auto" and can_install:
                got = dir_size(app)
                if not main:
                    log("После распаковки главный exe не найден.")
                    do_install = True
                elif bins and got < bin_size:
                    log(f"Распаковано {fmt_size(got)}, а в .bin лежит {fmt_size(bin_size)}: "
                        "похоже на репак, данные которого ставит сам установщик.")
                    do_install = True
                elif bins:
                    log("Предупреждение: рядом есть .bin файлы. Если программа не запустится "
                        "или ей не хватает данных, повторите в режиме 'Только установка (в App)'.")

            if do_install:
                extracted = target / "Extracted"
                log(f"Пробую тихую установку. Распакованные файлы сохраню в {extracted}.")
                try:
                    app.rename(extracted)
                except OSError as e:
                    log(f"Не удалось переместить распакованное: {e}")
                    do_install = False

        if do_install:
            if silent_install(exe, kind, app, log, job):
                main = resolve_manual(app, manual_exe, log) or find_main_exe(app, log, info.get('chooser'))
            else:
                main = None
                # установка не удалась: возвращаем распакованное на место, чтобы его можно было использовать
                extracted = target / "Extracted"
                try:
                    if extracted.is_dir() and not any(app.iterdir()):
                        app.rmdir()
                        extracted.rename(app)
                        log("Установка не удалась - распакованные файлы возвращены в App.")
                        main = resolve_manual(app, manual_exe, log) or find_main_exe(app, log, info.get('chooser'))
                except OSError as e:
                    log(f"Не удалось вернуть распакованное в App: {e}")

    if not main:
        log("Главный exe не найден.")
        report_location(target, app, log)
        log_exe_candidates(app if any(app.rglob("*.exe")) else target, log)
        log("Укажите exe в поле 'Главный exe' и запустите режим 'Только Launch.bat'.")
        return False
    return finish(target, app, main, log, info, direct_unreal=not (manual_exe or "").strip())


def portabilize(exe_path, out_root, log, mode="auto", manual_exe="", job=None, history=None,
                chooser=None, radical=False, confirmed=False, dx_prompt=None, shortcut_prompt=None):
    """Главная функция: конвертация + учёт в истории + поддержка паузы/отмены через job.

    radical=True (режим R): после успешной сборки удаляет исходный файл и временные копии.
    Результат создаётся рядом с исходником. Без confirmed=True ничего не делается."""
    exe = Path(exe_path) if str(exe_path).strip() else None
    EXTRACT_WARNINGS.clear()
    if radical and mode == "launcher":
        radical = False                      # Launch.bat не создаёт копий: удалять нечего
    if radical:
        if not confirmed:
            log("Радикальный режим не подтверждён: ничего не делаю.")
            return False
        if exe is None or not exe.is_file():
            log("Файл не найден.")
            return False
        out_root = str(exe.parent)           # «на месте»: результат рядом с исходным файлом
    rec = None
    if history is not None and exe is not None:
        try:
            size = exe.stat().st_size if exe.is_file() else 0
        except OSError:
            size = 0
        rec = history.add(source=str(exe), source_size=size, target="", mode=mode,
                          kind="", status="running", started=now_iso(), finished="",
                          main_exe="", note="", radical=bool(radical))
    info = {"set_target": (lambda p: history.update(rec["id"], target=p)) if rec
            else (lambda p: None), "chooser": chooser, "radical": bool(radical),
            "dx_prompt": dx_prompt, "shortcut_prompt": shortcut_prompt}
    ok, status = False, "failed"
    try:
        if job:
            if job.cancelled:
                raise JobCancelled()
            if mode != "launcher":
                job.watch(Path(out_root).resolve())
        ok = _portabilize(exe_path, out_root, log, mode, manual_exe, None, job, info)
        if job and job.cancelled:
            status = "canceled"
        else:
            status = "done" if ok else "failed"
        if ok and radical and status == "done" and info.get("target"):
            res = radical_cleanup(exe, Path(info["target"]), info, log, job)
            if job is not None:
                job.radical_result = res
            if rec:
                history.update(rec["id"], freed=res["freed"], source_deleted=bool(res["deleted"]),
                               note_radical=res["kept_reason"])
        if ok and mode == "launcher" and rec:
            history.update(rec["id"], target=str((Path(out_root).resolve()
                                                   / f"{clean_stem(exe)}_portable")))
    except JobCancelled:
        if job and not job.cancelled:
            job.cancel()
        log("Прервано пользователем. Частично созданные файлы остались на диске: "
            "удалить их можно во вкладке «История».")
        ok, status = False, "canceled"
    except Exception as e:  # noqa
        log(f"Ошибка: {e}")
        ok, status = False, "failed"
    finally:
        if job:
            job.finished = True
        if rec:
            history.update(rec["id"], status=status, finished=now_iso(),
                           kind=info.get("kind", ""), main_exe=info.get("main", ""),
                           note="; ".join(info.get("notes", [])))
    return ok


# ------------------------------------------------------------------ проверка новой версии

APP_VERSION = "9.3"
UPDATE_URL = "https://api.github.com/repos/Vanyok-gh/Portabilizer/releases"


def _ver_tuple(tag) -> tuple:
    nums = tuple(int(x) for x in re.findall(r"\d+", str(tag or "")))
    return nums or (0,)


def check_update(current=APP_VERSION, url=UPDATE_URL, timeout=6, opener=None):
    """Ищет в GitHub Releases версию новее текущей (пробные версии пропускаем).
    Возвращает {"tag", "name", "notes", "page"} или None. Любые ошибки сети: None, без шума."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Portabilizer",
                                                   "Accept": "application/vnd.github+json"})
        with (opener or urllib.request.urlopen)(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:           # noqa: BLE001 - нет сети, лимит GitHub, неверный ответ
        return None
    best = None
    for rel in data if isinstance(data, list) else []:
        tag = str(rel.get("tag_name", "")) if isinstance(rel, dict) else ""
        if (not isinstance(rel, dict) or rel.get("draft") or rel.get("prerelease")
                or not re.match(r"^[vV]?\d", tag)):
            continue
        if _ver_tuple(tag) > _ver_tuple(current) and (best is None or _ver_tuple(tag) > _ver_tuple(best["tag"])):
            best = {"tag": tag, "name": rel.get("name") or tag, "notes": rel.get("body") or "",
                    "page": rel.get("html_url") or ""}
    return best


# ------------------------------------------------------------------ темы оформления

SETTINGS_FILE = "portabilizer_settings.json"
THEME_ROLES = ("bg", "surface", "surface2", "fg", "muted", "border", "accent", "accent_fg", "hover",
               "sel_bg", "sel_fg", "ok", "warn", "danger", "dis")
# Встроенные темы. Свои темы - файлы *.json в папке themes рядом с программой (те же ключи,
# плюс "name", "kind": "light" или "dark", "r": true для красных тем режима R).
THEMES_BUILTIN = {
    "light": {
        "name": "Светлая",
        "kind": "light",
        "r": False,
        "bg": "#f3f4f6",
        "surface": "#ffffff",
        "surface2": "#e4e7eb",
        "fg": "#1f2328",
        "muted": "#555e68",
        "border": "#c4c9d0",
        "accent": "#1f5fd1",
        "accent_fg": "#ffffff",
        "hover": "#1a4fb0",
        "sel_bg": "#cfe0ff",
        "sel_fg": "#111827",
        "ok": "#1a7f37",
        "warn": "#8a5a00",
        "danger": "#b3261e",
        "dis": "#8c959f"
    },
    "dark": {
        "name": "Тёмная",
        "kind": "dark",
        "r": False,
        "bg": "#1b1d21",
        "surface": "#23262b",
        "surface2": "#2e3238",
        "fg": "#e6e8eb",
        "muted": "#a3a9b1",
        "border": "#3d424a",
        "accent": "#3568be",
        "accent_fg": "#ffffff",
        "hover": "#4171c2",
        "sel_bg": "#2f4b7c",
        "sel_fg": "#ffffff",
        "ok": "#5fcf80",
        "warn": "#f0b45a",
        "danger": "#ff7b7b",
        "dis": "#6b727b"
    },
    "light_r": {
        "name": "Светло-красная (R)",
        "kind": "light",
        "r": True,
        "bg": "#fbf1f1",
        "surface": "#ffffff",
        "surface2": "#f1d9d9",
        "fg": "#2b1618",
        "muted": "#6a464a",
        "border": "#deb7b7",
        "accent": "#c62828",
        "accent_fg": "#ffffff",
        "hover": "#a61e1e",
        "sel_bg": "#f6c9c9",
        "sel_fg": "#2b1618",
        "ok": "#1f6f33",
        "warn": "#8a5200",
        "danger": "#b00020",
        "dis": "#a88a8c"
    },
    "dark_r_charcoal": {
        "name": "Уголь с красным акцентом",
        "kind": "dark",
        "r": True,
        "bg": "#18191c",
        "surface": "#212226",
        "surface2": "#2c2d32",
        "fg": "#ececee",
        "muted": "#a9aab0",
        "border": "#3d3e45",
        "accent": "#c8323d",
        "accent_fg": "#ffffff",
        "hover": "#ce444e",
        "sel_bg": "#5a2329",
        "sel_fg": "#ffffff",
        "ok": "#6fd08a",
        "warn": "#f0b45a",
        "danger": "#ff7f89",
        "dis": "#6c6d74"
    },
    "dark_r_wine": {
        "name": "Бордо",
        "kind": "dark",
        "r": True,
        "bg": "#1f1316",
        "surface": "#2b1b1f",
        "surface2": "#3b2429",
        "fg": "#f4e8e9",
        "muted": "#c7a9ac",
        "border": "#5c3b41",
        "accent": "#c4303b",
        "accent_fg": "#ffffff",
        "hover": "#ca424d",
        "sel_bg": "#6a2a32",
        "sel_fg": "#ffffff",
        "ok": "#72d38b",
        "warn": "#f2b865",
        "danger": "#ff8089",
        "dis": "#7d6366"
    },
    "dark_r_cherry": {
        "name": "Вишнёвая",
        "kind": "dark",
        "r": True,
        "bg": "#260d13",
        "surface": "#321219",
        "surface2": "#471b25",
        "fg": "#fbeaec",
        "muted": "#d4a6ad",
        "border": "#6e2c38",
        "accent": "#c8303f",
        "accent_fg": "#ffffff",
        "hover": "#ce4250",
        "sel_bg": "#7a2b37",
        "sel_fg": "#ffffff",
        "ok": "#78d68f",
        "warn": "#f5bb68",
        "danger": "#ff8a94",
        "dis": "#85606a"
    }
}
CLASSIC = {"bg": None, "surface": "white", "surface2": None, "fg": "black", "muted": "#666666",
           "border": None, "accent": None, "accent_fg": None, "hover": None, "sel_bg": "#0078d7",
           "sel_fg": "white", "ok": "#1b6e2d", "warn": "#b36b00", "danger": "#b00020", "dis": "#888888"}
APPEARANCES = {"auto": "Авто (как в Windows)", "light": "Светлая", "dark": "Тёмная",
               "classic": "Классическая (системная)"}


def _is_hex(v) -> bool:
    return isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v) is not None


def load_settings(path=None) -> dict:
    try:
        d = json.loads(Path(path or (app_dir() / SETTINGS_FILE)).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


RESTART = {"flag": False, "geometry": "", "radical": False}   # смена языка перезапускает окно (см. run_gui)


def init_language(settings: dict) -> str:
    """Язык из настроек; при первом запуске собранного exe - язык системы, иначе русский."""
    lang = settings.get("language")
    if not lang:
        lang = detect_lang() if getattr(sys, "frozen", False) else "ru"
    return set_lang(lang)


def save_settings(d: dict, path=None):
    pth = Path(path or (app_dir() / SETTINGS_FILE))
    try:
        tmp = pth.with_name(pth.name + ".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, pth)
    except OSError:
        pass


def load_themes(folder=None) -> dict:
    """Встроенные темы + пользовательские из папки themes. Битые файлы пропускаем."""
    themes = {k: dict(v, id=k) for k, v in THEMES_BUILTIN.items()}
    d = Path(folder) if folder else app_dir() / "themes"
    try:
        files = sorted(d.glob("*.json")) if d.is_dir() else []
    except OSError:
        files = []
    for f in files:
        if f.stem.startswith("_"):             # _пример.json и подобные не загружаем
            continue
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(t, dict):
            continue
        kind = t.get("kind") if t.get("kind") in ("light", "dark") else "light"
        base = dict(THEMES_BUILTIN["dark_r_charcoal" if t.get("r") and kind == "dark" else
                                   "light_r" if t.get("r") else kind])
        for role in THEME_ROLES:                # недостающие цвета берём из базовой темы
            if _is_hex(t.get(role)):
                base[role] = t[role]
        base.update(name=str(t.get("name") or f.stem), kind=kind, r=bool(t.get("r")), id=f.stem,
                    user=True)
        themes[f.stem] = base
    return themes


def system_prefers_dark() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except (OSError, ImportError):
        return False


def pick_theme(settings: dict, radical: bool, themes: dict, dark_system=None):
    """Какую тему применить. None - классический системный вид (ничего не красим)."""
    ap = settings.get("appearance", "auto")
    if ap == "classic":
        return None
    if ap in themes and not themes[ap].get("r"):
        kind = themes[ap]["kind"]
    elif ap == "dark":
        kind = "dark"
    elif ap == "light":
        kind = "light"
    else:
        kind = "dark" if (system_prefers_dark() if dark_system is None else dark_system) else "light"
    if radical:
        want = settings.get("dark_r" if kind == "dark" else "light_r", "")
        t = themes.get(want)
        if t and t.get("r") and t["kind"] == kind:
            return t
        return themes["dark_r_charcoal" if kind == "dark" else "light_r"]
    if ap in themes and not themes[ap].get("r"):
        return themes[ap]
    return themes[kind]


def _mix(a: str, b: str, t: float) -> str:
    a, b = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join(f"{round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t):02x}"
                         for i in (0, 2, 4))


def _lum(h: str) -> float:
    h = h.lstrip("#")
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4   # noqa
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def make_theme_from_color(accent: str, kind: str = "dark", bg_tint=None, name="Мой цвет",
                          radical=False) -> dict:
    """Полная палитра из одного выбранного цвета (и необязательного оттенка фона).
    Цвета подгоняются так, чтобы текст везде читался (контраст не ниже 4,5:1)."""
    import colorsys
    if not _is_hex(accent):
        raise ValueError("цвет должен быть вида #rrggbb")
    rgb = lambda h: tuple(int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))   # noqa
    hexc = lambda r, g, b: "#%02x%02x%02x" % tuple(round(max(0, min(1, v)) * 255) for v in (r, g, b))  # noqa
    ah, _al, asat = colorsys.rgb_to_hls(*rgb(accent))
    th = colorsys.rgb_to_hls(*rgb(bg_tint if _is_hex(bg_tint) else accent))[0]
    dark = kind == "dark"
    sat = 0.22 if dark else 0.30
    hls = lambda h, l, sa: hexc(*colorsys.hls_to_rgb(h, l, sa))                       # noqa
    if dark:
        bg, surface, surface2 = hls(th, 0.10, sat), hls(th, 0.14, sat), hls(th, 0.20, sat)
        fg, border, sel_bg = hls(th, 0.93, 0.25), hls(th, 0.28, sat), hls(ah, 0.30, max(asat, .35))
        sel_fg = "#ffffff"
        ok, warn, danger = "#6fd08a", "#f0b45a", "#ff8088"
    else:
        bg, surface, surface2 = hls(th, 0.96, sat), "#ffffff", hls(th, 0.89, sat)
        fg, border, sel_bg = hls(th, 0.11, 0.30), hls(th, 0.78, sat), hls(ah, 0.86, max(asat, .45))
        sel_fg = hls(th, 0.11, 0.30)
        ok, warn, danger = "#1a7f37", "#8a5a00", "#b3261e"
    if dark:                                    # выделение: белый текст на нём должен читаться
        sh, sl, ss = colorsys.rgb_to_hls(*rgb(sel_bg))
        for _ in range(40):
            if contrast("#ffffff", sel_bg) >= 4.6:
                break
            sl = max(0.0, sl - 0.02)
            sel_bg = hls(sh, sl, ss)
    # акцент: подгоняем яркость, чтобы белый текст на нём читался
    h, l, sa = colorsys.rgb_to_hls(*rgb(accent))
    sa = max(sa, 0.45)
    acc = hls(h, l, sa)
    for _ in range(40):
        if contrast("#ffffff", acc) >= 4.6:
            break
        l = max(0.0, l - 0.02)
        acc = hls(h, l, sa)
    hover = hls(h, max(0.0, l - 0.05), sa)
    if contrast("#ffffff", hover) < 4.5:
        hover = acc
    # второстепенный текст: двигаем яркость, пока не станет читаться на фоне и на полях
    mh = th
    ml = 0.70 if dark else 0.34
    muted = hls(mh, ml, 0.12)
    for _ in range(40):
        if min(contrast(muted, bg), contrast(muted, surface), contrast(muted, surface2)) >= 4.5:
            break
        ml = min(1.0, ml + 0.02) if dark else max(0.0, ml - 0.02)
        muted = hls(mh, ml, 0.12)
    dis = hls(th, 0.45, 0.10)
    t = dict(name=name, kind=kind, r=bool(radical), bg=bg, surface=surface, surface2=surface2, fg=fg,
             muted=muted, border=border, accent=acc, accent_fg="#ffffff", hover=hover,
             sel_bg=sel_bg, sel_fg=sel_fg, ok=ok, warn=warn, danger=danger, dis=dis)
    return t


def ttk_style_spec(c: dict) -> list:
    """Описание стилей ttk для палитры c: список (имя_стиля, configure, map).
    Чистая функция: так её можно проверять без окна."""
    bg, sf, sf2, fg, mu, bd = c["bg"], c["surface"], c["surface2"], c["fg"], c["muted"], c["border"]
    ac, acf, hv = c["accent"], c["accent_fg"], c["hover"]
    sb, sfg, dis = c["sel_bg"], c["sel_fg"], c["dis"]
    hov2 = _mix(sf2, fg, 0.10)
    press = _mix(sf2, fg, 0.18)
    flat = dict(lightcolor=sf2, darkcolor=sf2, bordercolor=bd)
    return [
        (".", dict(background=bg, foreground=fg, bordercolor=bd, troughcolor=sf2, focuscolor=ac,
                   selectbackground=sb, selectforeground=sfg, insertcolor=fg, fieldbackground=sf,
                   lightcolor=bg, darkcolor=bg), {"foreground": [("disabled", dis)]}),
        ("TFrame", dict(background=bg), {}),
        ("TLabel", dict(background=bg, foreground=fg), {}),
        ("Muted.TLabel", dict(foreground=mu), {}),
        ("Warn.TLabel", dict(foreground=c["warn"]), {}),
        ("Danger.TLabel", dict(foreground=c["danger"]), {}),
        ("TLabelframe", dict(background=bg, bordercolor=bd, lightcolor=bg, darkcolor=bg), {}),
        ("TLabelframe.Label", dict(background=bg, foreground=fg), {}),
        ("TButton", dict(background=sf2, foreground=fg, padding=(10, 4), relief="flat", **flat),
         {"background": [("disabled", sf2), ("pressed", press), ("active", hov2)],
          "foreground": [("disabled", dis)],
          "bordercolor": [("focus", ac)]}),
        ("Accent.TButton", dict(background=ac, foreground=acf, padding=(12, 5), relief="flat",
                                lightcolor=ac, darkcolor=ac, bordercolor=ac),
         {"background": [("disabled", sf2), ("pressed", hv), ("active", hv)],
          "foreground": [("disabled", dis)],
          "bordercolor": [("disabled", bd)], "lightcolor": [("disabled", sf2), ("active", hv)],
          "darkcolor": [("disabled", sf2), ("active", hv)]}),
        ("TNotebook", dict(background=bg, bordercolor=bd, lightcolor=bg, darkcolor=bg,
                           tabmargins=(2, 4, 2, 0)), {}),
        ("TNotebook.Tab", dict(background=sf2, foreground=mu, padding=(12, 5), bordercolor=bd,
                               lightcolor=sf2, darkcolor=sf2),
         {"background": [("selected", sf), ("active", hov2)],
          "foreground": [("selected", fg), ("active", fg)],
          "lightcolor": [("selected", sf)], "darkcolor": [("selected", sf)]}),
        ("TEntry", dict(fieldbackground=sf, foreground=fg, insertcolor=fg, bordercolor=bd,
                        lightcolor=sf, darkcolor=sf, padding=3),
         {"bordercolor": [("focus", ac)], "lightcolor": [("focus", ac)], "darkcolor": [("focus", ac)]}),
        ("TCombobox", dict(fieldbackground=sf, background=sf2, foreground=fg, arrowcolor=fg,
                           insertcolor=fg, bordercolor=bd, lightcolor=sf, darkcolor=sf, padding=3,
                           selectbackground=sf, selectforeground=fg),
         {"fieldbackground": [("readonly", sf), ("disabled", sf2)],
          "foreground": [("readonly", fg), ("disabled", dis)],
          "background": [("active", hov2), ("readonly", sf2)],
          "bordercolor": [("focus", ac)], "arrowcolor": [("disabled", dis)]}),
        ("TProgressbar", dict(troughcolor=sf2, background=ac, bordercolor=bd, lightcolor=ac,
                              darkcolor=ac, thickness=14), {}),
        ("TScrollbar", dict(background=sf2, troughcolor=bg, bordercolor=bd, arrowcolor=fg,
                            lightcolor=sf2, darkcolor=sf2, relief="flat"),
         {"background": [("active", hov2), ("pressed", press)]}),
        ("Treeview", dict(background=sf, fieldbackground=sf, foreground=fg, bordercolor=bd,
                          lightcolor=sf, darkcolor=sf, rowheight=22),
         {"background": [("selected", sb)], "foreground": [("selected", sfg)]}),
        ("Treeview.Heading", dict(background=sf2, foreground=fg, relief="flat", bordercolor=bd,
                                  lightcolor=sf2, darkcolor=sf2, padding=(6, 4)),
         {"background": [("active", hov2)]}),
        ("TCheckbutton", dict(background=bg, foreground=fg, indicatorcolor=sf, bordercolor=bd), 
         {"indicatorcolor": [("selected", ac)], "background": [("active", bg)]}),
        ("TRadiobutton", dict(background=bg, foreground=fg, indicatorcolor=sf, bordercolor=bd),
         {"indicatorcolor": [("selected", ac)], "background": [("active", bg)]}),
        ("TSeparator", dict(background=bd), {}),
    ]


def set_dark_titlebar(root, dark: bool):
    """Тёмная рамка окна в Windows 10/11 (если система это умеет). Ошибки не критичны."""
    if os.name != "nt":
        return
    try:
        import ctypes
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        val = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):                   # 20 - Windows 11 и поздние 10, 19 - ранние 10
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), 4) == 0:
                break
    except Exception:
        pass


# ------------------------------------------------------------------ интерфейс

def gui(_hook=None, start_radical=False):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    if os.name == "nt":
        try:                                  # чтобы в панели задач была наша иконка, а не Python
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Portabilizer.Desktop")
        except Exception:
            pass
    root = tk.Tk()
    root.title("Portabilizer")
    ver = {"radical": False}
    icon_refs = {}

    def set_icon(radical, classic=False):
        try:                                  # «Классическая» тема - пиксельные перья, остальные - гладкие
            key = "red" if radical else "blue"
            src = ICONS_PX if classic else ICONS
            imgs = [tk.PhotoImage(data=src[f"{key}{n}"]) for n in (64, 32)]
            icon_refs["imgs"] = imgs          # ссылки нужны, иначе картинки удалит сборщик мусора
            root.iconphoto(True, *imgs)
        except Exception:
            pass

    root.geometry(RESTART["geometry"] or "880x720")
    root.minsize(800, 620)

    history = History()
    settings = load_settings()
    init_language(settings)
    state = {"job": None}
    advisor = Advisor()
    mode_names = {
        tr("Авто"): "auto",
        tr("Только распаковка"): "extract",
        tr("Только установка (в App)"): "install",
        tr("Только Launch.bat"): "launcher",
    }
    mode_by_value = {v: k for k, v in mode_names.items()}

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)
    main_tab, hist_tab, diag_tab, ver_tab, iso_tab, look_tab, lang_tab = (
        ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb))
    nb.add(main_tab, text=tr("Конвертер"))
    nb.add(hist_tab, text=tr("История"))
    nb.add(diag_tab, text=tr("Диагностика"))
    nb.add(ver_tab, text=tr("Версии"))
    nb.add(iso_tab, text=tr("Образ ISO"))
    nb.add(look_tab, text=tr("Оформление"))
    nb.add(lang_tab, text=tr("Язык"))

    # ---------------------------------------------------------- вкладка «Конвертер»
    src, dst = tk.StringVar(), tk.StringVar(value=str(Path.cwd()))
    mexe = tk.StringVar()
    mode_var = tk.StringVar(value=tr("Авто"))
    run_names = {tr("Авто (без UAC, если exe просит админа)"): "auto",
                 tr("Всегда без UAC"): "noadmin", tr("Всегда с UAC (как в оригинале)"): "admin"}
    run_var = tk.StringVar(value=next(iter(run_names)))
    status_var = tk.StringVar(value=tr("Готов к работе."))
    main_tab.grid_columnconfigure(1, weight=1)
    main_tab.grid_rowconfigure(9, weight=1)

    def row(r, label, var, cmd):
        ttk.Label(main_tab, text=label).grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(main_tab, textvariable=var, width=60).grid(row=r, column=1, padx=4, sticky="ew")
        ttk.Button(main_tab, text="...", width=4, command=cmd).grid(row=r, column=2, padx=4)

    patterns = ("*.exe *.msi *.msix *.appx *.msixbundle *.appxbundle "
                "*.rar *.zip *.7z *.tar *.gz *.tgz *.xz *.bz2 *.cab *.iso")
    row(0, tr("Файл:"), src, lambda: src.set(filedialog.askopenfilename(
        filetypes=[(tr("Установщики, пакеты, архивы"), patterns), (tr("Все"), "*.*")]) or src.get()))
    row(1, tr("Куда:"), dst, lambda: dst.set(filedialog.askdirectory() or dst.get()))
    row(2, tr("Главный exe:"), mexe, lambda: mexe.set(filedialog.askopenfilename(
        filetypes=[(tr("Программы"), "*.exe"), (tr("Все"), "*.*")]) or mexe.get()))

    ttk.Label(main_tab, text=tr("Режим:")).grid(row=3, column=0, sticky="w", padx=8, pady=6)
    mrow = ttk.Frame(main_tab)
    mrow.grid(row=3, column=1, sticky="w", padx=4)
    combos = []
    combos.append(ttk.Combobox(mrow, textvariable=mode_var, values=list(mode_names),
                               state="readonly", width=30))
    combos[-1].pack(side="left")
    ttk.Label(mrow, text=tr("   Запуск:")).pack(side="left")
    combos.append(ttk.Combobox(mrow, textvariable=run_var, values=list(run_names),
                               state="readonly", width=40))
    combos[-1].pack(side="left", padx=4)

    hint = (tr("Файл: exe, msi, msix/appx, архив (rar, zip, 7z...). Главный exe - необязательно: "
            "имя (App.exe), путь внутри App или файл из папки App. "
            "Лог сохраняется в portabilizer.log."))
    hint_lbl = ttk.Label(main_tab, text=hint, wraplength=820, style="Muted.TLabel")
    hint_lbl.grid(row=4, column=0, columnspan=3, sticky="w", padx=8)

    bf = ttk.Frame(main_tab)
    bf.grid(row=5, column=0, columnspan=3, pady=6)
    btn_start = ttk.Button(bf, text=tr("Сделать портативным"), style="Accent.TButton")
    btn_pause = ttk.Button(bf, text=tr("Пауза"))
    btn_resume = ttk.Button(bf, text=tr("Продолжить"))
    btn_cancel = ttk.Button(bf, text=tr("Прервать"))
    for b in (btn_start, btn_pause, btn_resume, btn_cancel):
        b.pack(side="left", padx=4)

    pb = ttk.Progressbar(main_tab, mode="determinate", maximum=100)
    pb.grid(row=6, column=0, columnspan=3, sticky="ew", padx=8)
    ttk.Label(main_tab, textvariable=status_var, style="Muted.TLabel").grid(
        row=7, column=0, columnspan=3, sticky="w", padx=8, pady=2)

    tipf = ttk.LabelFrame(main_tab, text=tr("Рекомендации"))
    tipf.grid(row=8, column=0, columnspan=3, sticky="ew", padx=8, pady=4)
    tips = tk.Text(tipf, height=5, wrap="word", state="disabled", relief="flat")
    tips.pack(fill="x", padx=4, pady=2)
    tips.tag_config("info", foreground="#555555")
    tips.tag_config("warn", foreground="#b36b00")
    tips.tag_config("danger", foreground="#b00020")

    logf = ttk.Frame(main_tab)
    logf.grid(row=9, column=0, columnspan=3, sticky="nsew", padx=8, pady=6)
    box = tk.Text(logf, height=10, state="disabled", wrap="word")
    sb = ttk.Scrollbar(logf, command=box.yview)
    box.config(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    box.pack(side="left", fill="both", expand=True)

    def refresh_tips():
        tips.config(state="normal")
        tips.delete("1.0", "end")
        if not advisor.items:
            tips.insert("end", tr("Пока всё спокойно. Здесь появятся подсказки при нехватке места "
                               "и типовых ошибках."), "info")
        marks = {"info": "• ", "warn": "! ", "danger": "!! "}
        for _ts, level, text in advisor.items:
            tips.insert("end", marks.get(level, "• ") + trx(text) + "\n", level)
        tips.config(state="disabled")
        tips.see("end")

    advisor.on_change = lambda: root.after(0, refresh_tips)
    refresh_tips()

    def ui_log(msg):
        advisor.scan(msg)

        def _w():
            box.config(state="normal")
            box.insert("end", trx(msg) + "\n")
            box.see("end")
            box.config(state="disabled")
        root.after(0, _w)

    log = make_logger(ui_log)

    def ask_ui(kind, title, text, **kw):
        """Диалог из рабочего потока (вызывать только не из главного потока)."""
        ev, res = threading.Event(), {}

        def _do():
            res["v"] = getattr(messagebox, kind)(title, text, parent=root, **kw)
            ev.set()
        root.after(0, _do)
        ev.wait()
        return res.get("v")

    def dx_ui(text):
        v = ask_ui("askyesnocancel", tr("Нужен DirectX"), text, icon="question")
        return "install" if v is True else "skip" if v is False else "cancel"

    def shortcut_ui(name, has_icon):
        text = tr("Создать ярлык «{0}» на рабочем столе?\n\nПо двойному щелчку программа запустится из этой папки.", name)
        text += tr("\nИконка берётся из самой программы.") if has_icon else tr("\nИконку программы найти не удалось: ярлык будет со стандартной.")
        text += tr("\n\nЕсли папку потом переместить, запустите Create_Shortcut.bat из неё: ярлык создастся заново.")
        return bool(ask_ui("askyesno", tr("Ярлык на рабочем столе"), text, icon="question"))

    def set_buttons(st):
        on, off = ["!disabled"], ["disabled"]
        btn_start.state(off if st != "idle" else on)
        btn_pause.state(on if st == "running" else off)
        btn_resume.state(on if st == "paused" else off)
        btn_cancel.state(on if st in ("running", "paused") else off)
        state["buttons"] = st

    set_buttons("idle")

    low_dlg = {"win": None, "text": "", "fits": None, "choose": None}

    def low_space_text(job, base):
        """Текст окна: сколько осталось записать и хватит ли места. Второе значение: хватит ли."""
        free = job.free_bytes()
        rem = job.remaining_bytes()
        lines = [base]
        fits = None
        if free is not None and rem is not None:
            fits = rem + HARD_FLOOR <= free
            if fits:
                lines.append(tr("Осталось записать примерно {0}, свободно {1}: этого должно хватить, можно дотянуть до конца.", fmt_size(rem), fmt_size(free)))
            else:
                lines.append(tr("Осталось записать примерно {0}, а свободно {1}: не хватит примерно на {2}.", fmt_size(rem), fmt_size(free), fmt_size(rem + HARD_FLOOR - free)))
        else:
            lines.append(tr("Сколько ещё осталось записать, точно сказать нельзя."))
        lines.append(tr("Загрузка стоит на паузе, ничего не потеряно. Отмена остановит работу насовсем: "
                     "потом можно только начать заново («Повторить» во вкладке «История»)."))
        return "\n\n".join(lines), fits

    def show_low_space(base_text):
        """Окно с тремя вариантами. Показывается один раз, пока открыто."""
        job = state["job"]
        if not job or job.finished or low_dlg["win"] is not None:
            return
        text, fits = low_space_text(job, base_text)
        win = tk.Toplevel(root)
        win.title(tr("Заканчивается место на диске"))
        win.transient(root)
        win.resizable(False, False)
        try:
            win.attributes("-topmost", True)    # чтобы окно не потерялось за другими программами
            win.focus_force()
        except Exception:
            pass
        ttk.Label(win, text=text, wraplength=480, justify="left").pack(padx=16, pady=(16, 8))
        row_ = ttk.Frame(win)
        row_.pack(pady=(4, 16))

        def choose(what):
            try:
                win.destroy()
            except Exception:
                pass
            low_dlg["win"] = None
            j = state["job"]
            if not j or j.finished:
                return
            if what == "continue":
                if fits is False and not messagebox.askyesno(
                        tr("Не хватит места"),
                        tr("По оценке места не хватит. Если место кончится, распаковка остановится с "
                        "ошибкой.\n\nВсё равно продолжить?"), icon="warning", default="no",
                        parent=root):
                    log("Остаюсь на паузе. Освободите место и нажмите «Продолжить».")
                    return
                if j.force_resume(HARD_FLOOR):
                    log(f"Продолжаю на свой риск: остановлюсь, только если свободно станет "
                        f"меньше {fmt_size(HARD_FLOOR)}.")
                    set_buttons("running")
            elif what == "stop":
                log("Пауза. Освободите место на диске и нажмите «Продолжить».")
            elif what == "cancel":
                log("Загрузка отменяется по вашему выбору.")
                j.cancel()
        ttk.Button(row_, text=tr("Продолжить"), command=lambda: choose("continue")).pack(side="left", padx=5)
        ttk.Button(row_, text=tr("Остановить: почищу диск"),
                   command=lambda: choose("stop")).pack(side="left", padx=5)
        ttk.Button(row_, text=tr("Отменить загрузку"),
                   command=lambda: choose("cancel")).pack(side="left", padx=5)
        win.protocol("WM_DELETE_WINDOW", lambda: choose("stop"))
        low_dlg.update(win=win, text=text, fits=fits, choose=choose)

    def on_job_event(kind, text):
        if kind == "low_space":
            advisor.add("danger", text + tr(" Задача на паузе: выберите в окне, что делать."),
                        key="low_space", cooldown=5)
            root.after(0, lambda: show_low_space(text))

    chooser_dlg = {"win": None}

    def choose_exe_ui(options):
        """Окно выбора программы (вызывается из рабочего потока). Возвращает путь или None."""
        ev, res = threading.Event(), {}

        def pick(path):
            res["p"] = path
            win = chooser_dlg.get("win")
            chooser_dlg["win"] = None
            try:
                win.destroy()
            except Exception:
                pass
            ev.set()

        def show():
            win = tk.Toplevel(root)
            chooser_dlg["win"] = win
            win.title(tr("Какую программу запускать?"))
            win.transient(root)
            try:
                win.attributes("-topmost", True)
                win.focus_force()
            except Exception:
                pass
            ttk.Label(win, wraplength=520, justify="left", text=(
                tr("Нашлось несколько подходящих программ, и я не уверен, какая главная. "
                "Выберите ту, что запускает нужное приложение (её можно будет сменить позже "
                "в режиме «Только Launch.bat»)."))).pack(padx=16, pady=(16, 8))
            for label, path in options:
                ttk.Button(win, text=label,
                           command=lambda p=path: pick(p)).pack(fill="x", padx=16, pady=2)
            ttk.Button(win, text=tr("Выбрать автоматически"),
                       command=lambda: pick(None)).pack(padx=16, pady=(8, 16))
            win.protocol("WM_DELETE_WINDOW", lambda: pick(None))
        root.after(0, show)
        while not ev.wait(0.5):
            job = state["job"]
            if job is None or job.cancelled:
                break
        return res.get("p")

    def go():
        if state["job"]:
            return
        src_p, dst_p = src.get().strip(), dst.get().strip() or "."
        if not src_p:
            messagebox.showwarning("Portabilizer", tr("Выберите файл."), parent=root)
            return
        mode = mode_names.get(mode_var.get(), "auto")
        RUN_POLICY["value"] = run_names.get(run_var.get(), "auto")
        radical = ver["radical"] and mode != "launcher"
        if radical:
            sp = Path(src_p)
            if not sp.is_file():
                messagebox.showwarning("Portabilizer (R)", tr("Файл не найден."), parent=root)
                return
            files = [f for f in source_group(sp) if f.exists()]
            total = sum(f.stat().st_size for f in files)
            listing = "\n".join(f"  {f.name}  ({fmt_size(f.stat().st_size)})" for f in files[:8])
            if len(files) > 8:
                listing += tr("\n  ... и ещё {0}", len(files) - 8)
            try:
                is_plain = detect_type(sp) == "plain"
            except OSError:
                is_plain = False
            if is_plain:
                if not messagebox.askyesno(
                        tr("Portabilizer (R): файл будет перенесён"),
                        tr("{0} ({1}) будет ПЕРЕНЕСЁН в папку App рядом с собой: копии не создаётся, дополнительное место не нужно.\n\nНа прежнем месте файла больше не будет. Вернуть его можно, достав из папки App.\n\nПродолжить?", sp.name, fmt_size(total)), icon="warning", default="no", parent=root):
                    return
            elif not messagebox.askyesno(
                    tr("Portabilizer (R): исходный файл будет удалён"),
                    tr("Вы правда хотите сделать этот файл портативным в радикальном режиме?\n\nПосле успешной сборки будут УДАЛЕНЫ НАВСЕГДА (мимо корзины):\n{0}\nвсего {1}, а также временные копии.\n\nВернуть исходный файл потом будет нельзя. Если что-то пойдёт не так (например, игра не запустится), его придётся скачивать или ставить с платформы заново.\n\nУдаление произойдёт только если сборка удалась и всё проверено; при ошибке или отмене файл останется. Результат будет создан рядом с исходным файлом.\n\nПродолжить?", listing, fmt_size(total)),
                    icon="warning", default="no", parent=root):
                return
            dst_p = str(sp.parent)
            dst.set(dst_p)
        job = Job(on_event=on_job_event)
        state["job"] = job
        box.config(state="normal")
        box.delete("1.0", "end")
        box.config(state="disabled")
        set_buttons("running")

        def work():
            ok = False
            try:
                if mode != "launcher" and Path(src_p).is_file():
                    job.stage = tr("Оценка нужного места")
                    pre = preflight(Path(src_p), Path(dst_p), mode, radical)
                    if pre.get("exact"):
                        job.expected_total = pre["total"]
                    if pre["level"] != "ok":
                        advisor.add("danger" if pre["level"] == "danger" else "warn", pre["text"],
                                    key="preflight", cooldown=0)
                        go_on = ask_ui("askyesno", tr("Хватит ли места?"),
                                       pre["text"] + tr("\n\nНачать всё равно?"), icon="warning",
                                       default="no" if pre["level"] == "danger" else "yes")
                        if not go_on:
                            log("Отменено перед стартом: мало места на диске.")
                            job.declined = True
                            job.finished = True
                            return
                job.stage = tr("Подготовка")
                ok = portabilize(src_p, dst_p, log, mode, mexe.get(), job=job, history=history,
                                 chooser=choose_exe_ui, radical=radical, confirmed=radical,
                                 dx_prompt=dx_ui, shortcut_prompt=shortcut_ui)
            except Exception as e:  # noqa
                log(f"Ошибка: {e}")
            finally:
                root.after(0, lambda: on_finished(job, ok))
        threading.Thread(target=work, daemon=True).start()

    def on_finished(job, ok):
        state["job"] = None
        set_buttons("idle")
        pb.stop()
        pb.config(mode="determinate", value=100 if ok else 0)
        pb_state["mode"] = "determinate"
        if getattr(job, "declined", False):
            status_var.set(tr("Отменено перед стартом: мало места на диске."))
        elif job.cancelled:
            status_var.set(tr("Прервано. Остатки можно удалить во вкладке «История»."))
        else:
            res = getattr(job, "radical_result", None)
            if ok and res and res.get("moved"):
                status_var.set(tr("Готово. Файл перенесён без копии: дополнительного места не занято."))
            elif ok and res and res["deleted"]:
                status_var.set(tr("Готово. Исходный файл удалён, освобождено {0}.", fmt_size(res['freed'])))
            elif ok and res:
                status_var.set(tr("Готово, но исходный файл не удалён: ") + trx(res["kept_reason"]) + ".")
            else:
                status_var.set(tr("Готово. Результат - во вкладке «История».") if ok
                               else tr("Не получилось. Подробности - в логе и в рекомендациях."))
        refresh_history()

    def do_pause():
        job = state["job"]
        if job and job.pause("user"):
            log("Пауза: процесс заморожен, прогресс сохранён.")
            set_buttons("paused")
        elif job:
            log("Поставить на паузу сейчас нельзя (нужен psutil: pip install psutil).")

    def do_resume():
        job = state["job"]
        if not job:
            return
        if job.pause_reason == "low_space":
            free = job.free_bytes()
            if free is not None and free < LOW_SPACE * 1.5:       # место так и не освободили
                show_low_space(tr("На диске по-прежнему мало места: {0}.", fmt_size(free)))
                return
        if job.resume():
            log("Продолжаю с того же места.")
            set_buttons("running")

    def do_cancel():
        job = state["job"]
        if job and messagebox.askyesno(
                tr("Прервать?"), tr("Остановить работу? Продолжить с места остановки потом нельзя: "
                             "во вкладке «История» будет «Повторить» (начнёт заново)."),
                icon="warning", parent=root):
            job.cancel()

    btn_start.config(command=go)
    btn_pause.config(command=do_pause)
    btn_resume.config(command=do_resume)
    btn_cancel.config(command=do_cancel)

    pb_state = {"mode": "determinate"}

    def tick():
        job = state["job"]
        if job and not job.finished:
            want = "paused" if job.paused else "running"
            if state.get("buttons") != want and not job.cancelled:
                set_buttons(want)
            p = job.progress
            if p is None:
                if pb_state["mode"] != "indeterminate":
                    pb.config(mode="indeterminate")
                    pb_state["mode"] = "indeterminate"
                    pb.start(12)
                if job.paused:
                    pb.stop()
            else:
                if pb_state["mode"] != "determinate":
                    pb.stop()
                    pb.config(mode="determinate")
                    pb_state["mode"] = "determinate"
                pb["value"] = p
            parts = [job.stage or tr("Работа")]
            if p is not None:
                parts.append(f"{p}%")
            parts.append(tr("прошло {0}", fmt_time(job.active_elapsed)))
            if p and p >= 3 and not job.paused:
                parts.append(tr("осталось ~{0}", fmt_time(job.active_elapsed * (100 - p) / p)))
            if job.paused:
                parts.insert(0, tr("ПАУЗА"))
            if job.watch_path:
                try:
                    free = shutil.disk_usage(existing_parent(job.watch_path)).free
                    parts.append(tr("свободно на диске {0}", fmt_size(free)))
                except OSError:
                    pass
            status_var.set(" · ".join(parts))
        root.after(500, tick)

    # ---------------------------------------------------------- вкладка «История»
    hist_tab.grid_columnconfigure(0, weight=1)
    hist_tab.grid_rowconfigure(0, weight=1)
    cols = ("date", "name", "ver", "kind", "status", "size", "result", "note")
    tv = ttk.Treeview(hist_tab, columns=cols, show="headings", selectmode="browse")
    for c, title, w in (("date", tr("Дата"), 110), ("name", tr("Источник"), 190), ("ver", tr("Версия"), 55),
                        ("kind", tr("Тип"), 80), ("status", tr("Статус"), 120), ("size", tr("Размер"), 75),
                        ("result", tr("Результат"), 170), ("note", tr("Заметки"), 190)):
        tv.heading(c, text=title)
        tv.column(c, width=w, anchor="w")
    tv.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
    hsb = ttk.Scrollbar(hist_tab, command=tv.yview)
    tv.config(yscrollcommand=hsb.set)
    hsb.grid(row=0, column=1, sticky="ns", pady=8)
    tv.tag_configure("done", foreground="#1b6e2d")
    tv.tag_configure("failed", foreground="#b00020")
    tv.tag_configure("canceled", foreground="#b36b00")
    tv.tag_configure("interrupted", foreground="#b36b00")

    def refresh_history():
        tv.delete(*tv.get_children())
        for rec in reversed(history.all()):
            t = rec.get("target") or ""
            if t:
                result = Path(t).name + ("" if Path(t).exists() else tr(" (нет на диске)"))
            else:
                result = "-"
            tv.insert("", "end", iid=rec["id"], tags=(rec.get("status", ""),), values=(
                (rec.get("started") or "").replace("T", " ")[:16],
                Path(rec.get("source", "")).name, "R" if rec.get("radical") else "",
                rec.get("kind", ""),
                trx(STATUS_RU.get(rec.get("status", ""), rec.get("status", ""))),
                fmt_size(rec.get("source_size", 0)), result,
                "; ".join(trx(x) for x in rec.get("note", "").split("; "))))

    def selected_rec():
        sel = tv.selection()
        if not sel:
            messagebox.showinfo(tr("История"), tr("Сначала выберите запись в списке."), parent=root)
            return None
        return history.get(sel[0])

    def busy():
        if state["job"]:
            messagebox.showwarning("Portabilizer", tr("Дождитесь окончания текущей задачи "
                                   "(или прервите её)."), parent=root)
            return True
        return False

    def open_result(_e=None):
        rec = selected_rec()
        if not rec:
            return
        t = Path(rec.get("target") or "")
        if not rec.get("target") or not t.exists():
            messagebox.showinfo(tr("История"), tr("Папки результата нет на диске."), parent=root)
            return
        bat = t / "Launch.bat"
        if not reveal(bat if bat.is_file() else t):
            messagebox.showinfo(tr("История"), tr("Откройте вручную:\n{0}", t), parent=root)

    def launch_result():
        rec = selected_rec()
        if not rec:
            return
        bat = Path(rec.get("target") or "") / "Launch.bat"
        if not bat.is_file():
            messagebox.showinfo(tr("История"), tr("Launch.bat не найден: конвертация не завершена."),
                                parent=root)
            return
        try:
            os.startfile(str(bat))
        except Exception as e:  # noqa
            messagebox.showinfo(tr("История"), tr("Запустите вручную:\n{0}\n\n{1}", bat, e), parent=root)

    def make_shortcut():
        rec = selected_rec()
        if not rec:
            return
        t = Path(rec.get("target") or "")
        if not (t / "Launch.bat").is_file():
            messagebox.showinfo(tr("История"), tr("Launch.bat не найден: конвертация не завершена."),
                                parent=root)
            return
        bat = t / "Create_Shortcut.bat"
        main_rel = rec.get("main_exe") or ""
        if main_rel and (t / "App" / main_rel).is_file():                    # перечитываем иконку заново
            try:
                bat, _n, _i = write_shortcut_script(t, t / "App", t / "App" / main_rel)
            except OSError:
                pass
        if not bat.is_file():
            messagebox.showinfo(tr("История"), tr("Не удалось подготовить ярлык: главный exe не найден."),
                                parent=root)
            return
        if create_desktop_shortcut(bat, log):
            messagebox.showinfo(tr("История"), tr("Ярлык «{0}» создан на рабочем столе.", shortcut_name(t)),
                                parent=root)
        else:
            messagebox.showinfo(tr("История"), tr("Ярлык создать не получилось. Запустите вручную:\n{0}", bat),
                                parent=root)

    def retry():
        rec = selected_rec()
        if not rec or busy():
            return
        if not Path(rec.get("source", "")).exists():
            messagebox.showinfo(tr("История"), tr("Исходного файла уже нет")
                                + (tr(" (его удалил радикальный режим)") if rec.get("source_deleted")
                                   else "") + tr(", поэтому повторить нельзя. Скачайте или "
                                "установите его заново."), parent=root)
            return
        src.set(rec.get("source", ""))
        mode_var.set(mode_by_value.get(rec.get("mode", "auto"), tr("Авто")))
        t = Path(rec.get("target") or "")
        if rec.get("target"):
            dst.set(str(t.parent))
        nb.select(main_tab)
        if rec.get("target") and t.exists():
            def work():
                size = dir_size(t)
                if not ask_ui("askyesno", tr("Начать заново?"),
                              tr("Папка уже существует (остаток прошлой попытки):\n{0}\nРазмер: {1}\n\nУдалить её и начать заново?", t, fmt_size(size)),
                              icon="warning", default="no"):
                    return
                log(f"Удаляю {t} ...")
                if delete_target(t, log):
                    root.after(0, go)
                else:
                    log("Не удалось удалить папку целиком. Закройте программы, которые её "
                        "используют, и повторите.")
            threading.Thread(target=work, daemon=True).start()
        else:
            go()

    def delete_portable():
        rec = selected_rec()
        if not rec or busy():
            return
        t = Path(rec.get("target") or "")
        if not rec.get("target") or not t.exists():
            messagebox.showinfo(tr("История"), tr("Папки результата нет на диске."), parent=root)
            return
        if not is_deletable_target(t):
            messagebox.showerror(tr("Удаление"), tr("Эта папка не похожа на созданную Portabilizer "
                                 "(нужны имя *_portable и Launch.bat с папкой App). "
                                 "Из осторожности не удаляю."), parent=root)
            return

        def work():
            size = dir_size(t)
            if not ask_ui("askyesno", tr("Удалить портативную копию?"),
                          tr("{0}\n\nРазмер: {1}\n\nПапка будет удалена безвозвратно. Исходный файл (установщик или архив) не затрагивается.", t, fmt_size(size)),
                          icon="warning", default="no"):
                return
            log(f"Удаляю {t} ...")
            ok = delete_target(t, log)
            log("Папка удалена." if ok else "Удалить удалось не всё: часть файлов занята программой.")
            root.after(0, refresh_history)
        threading.Thread(target=work, daemon=True).start()

    def delete_source():
        rec = selected_rec()
        if not rec or busy():
            return
        files = [f for f in source_group(Path(rec.get("source", ""))) if f.exists()]
        if not files:
            messagebox.showinfo(tr("История"), tr("Исходный файл не найден (возможно, уже удалён)."),
                                parent=root)
            return
        total = sum(f.stat().st_size for f in files)
        listing = "\n".join(f"{f.name}  ({fmt_size(f.stat().st_size)})" for f in files[:12])
        if len(files) > 12:
            listing += tr("\n... и ещё {0}", len(files) - 12)
        if not messagebox.askyesno(
                tr("Удалить исходный файл?"),
                tr("Будут удалены НАВСЕГДА (мимо корзины), всего {0}:\n\n{1}\n\nПапка: {2}\n\nЭто ваш исходный файл, восстановить его будет нельзя. Удалять?", fmt_size(total), listing, files[0].parent), icon="warning", default="no", parent=root):
            return
        for f in files:
            try:
                f.unlink()
                log(f"Удалён файл: {f}")
            except OSError as e:
                log(f"Не удалось удалить {f}: {e}")
        refresh_history()

    def forget():
        rec = selected_rec()
        if rec and messagebox.askyesno(tr("История"), tr("Убрать запись из списка? Файлы на диске не "
                                       "затрагиваются."), parent=root):
            history.remove(rec["id"])
            refresh_history()

    tv.bind("<Double-1>", open_result)
    hb = ttk.Frame(hist_tab)
    hb.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
    for text, cmd in ((tr("Открыть папку"), open_result), (tr("Запустить"), launch_result),
                      (tr("Ярлык на рабочий стол"), make_shortcut), (tr("Повторить"), retry), (tr("Удалить копию"), delete_portable),
                      (tr("Удалить исходный файл"), delete_source), (tr("Убрать из списка"), forget),
                      (tr("Обновить"), refresh_history)):
        ttk.Button(hb, text=text, command=cmd).pack(side="left", padx=3)
    refresh_history()

    # -------------------------------------------------------- вкладка «Диагностика»
    diag = ttk.Frame(diag_tab, padding=10)
    diag.pack(fill="both", expand=True)
    diag.grid_columnconfigure(1, weight=1)
    sysinfo = tk.StringVar(value=tr("Собираю сведения о системе..."))
    ttk.Label(diag, textvariable=sysinfo, justify="left", wraplength=800).grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

    def bar_row(r, title):
        ttk.Label(diag, text=title, width=14).grid(row=r, column=0, sticky="w", pady=3)
        bar = ttk.Progressbar(diag, mode="determinate", maximum=100)
        bar.grid(row=r, column=1, sticky="ew", padx=6)
        var = tk.StringVar(value=tr("н/д"))
        ttk.Label(diag, textvariable=var, width=42).grid(row=r, column=2, sticky="w")
        return bar, var

    cpu_bar, cpu_var = bar_row(1, tr("Процессор"))
    ram_bar, ram_var = bar_row(2, tr("Память"))
    gpu_bar, gpu_var = bar_row(3, tr("Видеокарта"))
    io_var = tk.StringVar(value=tr("Диск: н/д"))
    ttk.Label(diag, textvariable=io_var).grid(row=4, column=0, columnspan=3, sticky="w", pady=4)
    dcols = ("drive", "total", "free", "used")
    disks = ttk.Treeview(diag, columns=dcols, show="headings", height=7)
    for c, title, w in (("drive", tr("Диск"), 160), ("total", tr("Объём"), 110), ("free", tr("Свободно"), 110),
                        ("used", tr("Занято"), 90)):
        disks.heading(c, text=title)
        disks.column(c, width=w, anchor="w")
    disks.grid(row=5, column=0, columnspan=3, sticky="ew", pady=6)
    disks.tag_configure("low", foreground="#b00020")
    disks.tag_configure("target", font=("TkDefaultFont", 9, "bold"))
    if not psutil:
        ttk.Label(diag, style="Warn.TLabel", wraplength=800,
                  text=(tr("Нагрузка CPU/RAM недоступна: установите psutil (pip install psutil). "
                        "В собранном Portabilizer.exe он уже внутри."))
                  ).grid(row=6, column=0, columnspan=3, sticky="w")

    gpu_state = {"names": None, "data": None, "active": False}

    def gpu_worker():
        gpu_state["names"] = gpu_names()
        while True:
            if gpu_state["active"]:
                gpu_state["data"] = gpu_load()
            time.sleep(4)
    threading.Thread(target=gpu_worker, daemon=True).start()

    sys_static = {}
    prev_io = {"t": None, "r": 0, "w": 0}
    counter = {"n": 0}

    def update_diag():
        try:
            gpu_state["active"] = nb.index(nb.select()) == 2
            if not sys_static:
                ram_total = psutil.virtual_memory().total if psutil else 0
                cores = (tr("{0} ядер / {1} потоков", psutil.cpu_count(logical=False), psutil.cpu_count())
                         if psutil else "")
                sys_static["cpu"] = f"{cpu_name()} {('- ' + cores) if cores else ''}".strip()
                sys_static["ram"] = fmt_size(ram_total) if ram_total else tr("н/д")
                sys_static["os"] = f"{platform.system()} {platform.release()} ({platform.machine()})"
            names = gpu_state["names"]
            gpu_txt = tr("определяю...") if names is None else (", ".join(names) or tr("н/д"))
            sysinfo.set(tr("Система: {0}\nПроцессор: {1}\nОперативная память: {2}\nВидеокарта: {3}", sys_static['os'], sys_static['cpu'], sys_static['ram'], gpu_txt))
            if psutil:
                cpu = psutil.cpu_percent(interval=None)
                vm = psutil.virtual_memory()
                cpu_bar["value"] = cpu
                cpu_var.set(f"{cpu:.0f}%")
                ram_bar["value"] = vm.percent
                ram_var.set(tr("{0:.0f}%  ({1} из {2})", vm.percent, fmt_size(vm.used), fmt_size(vm.total)))
                if vm.percent > 92:
                    advisor.add("warn", tr("Оперативной памяти почти не осталось. Закройте браузер и "
                                        "лишние программы, иначе распаковка может сильно замедлиться."),
                                key="ram", cooldown=180)
                io = psutil.disk_io_counters()
                now = time.time()
                if io and prev_io["t"]:
                    dt = max(0.001, now - prev_io["t"])
                    io_var.set(tr("Диск: чтение {0}/с, запись {1}/с", fmt_size((io.read_bytes - prev_io['r']) / dt), fmt_size((io.write_bytes - prev_io['w']) / dt)))
                if io:
                    prev_io.update(t=now, r=io.read_bytes, w=io.write_bytes)
            data = gpu_state["data"]
            if data:
                gpu_bar["value"] = data["util"]
                extra = (tr(", память {0} из {1}, {2:.0f} °C", fmt_size(data['mem_used']), fmt_size(data['mem_total']), data['temp'])) if "mem_used" in data else tr(" (оценка по 3D)")
                gpu_var.set(f"{data['util']:.0f}%{extra}")
            elif gpu_state["names"] is not None:
                gpu_var.set(tr("нагрузка недоступна"))
            counter["n"] += 1
            if counter["n"] % 4 == 1:
                tgt = Path(dst.get() or ".").resolve().anchor
                disks.delete(*disks.get_children())
                for drive, total, used, free in list_drives():
                    tags = []
                    if free < DISK_WARN:
                        tags.append("low")
                    if tgt and drive.upper().startswith(tgt.upper()):
                        tags.append("target")
                    label = drive + (tr("  <- куда сохраняем") if "target" in tags else "")
                    disks.insert("", "end", values=(label, fmt_size(total), fmt_size(free),
                                                    f"{used * 100 // max(1, total)}%"),
                                 tags=tuple(tags))
                    if "low" in tags and "target" in tags:
                        advisor.add("warn", tr("На диске {0}, куда вы сохраняете, мало места ({1}). Выберите другой диск в поле «Куда».", drive, fmt_size(free)),
                                    key="lowdisk", cooldown=300)
        except Exception:
            pass
        root.after(1500, update_diag)

    # ------------------------------------------------------------ вкладка «Версии»
    ver_tab.grid_columnconfigure(0, weight=1)
    ver_tab.grid_columnconfigure(1, weight=1)
    ttk.Label(ver_tab, wraplength=820, text=(
        tr("Выберите, как Portabilizer делает портативные копии. Переключаться можно в любой момент "
        "(это лишь меняет режим работы). При каждом запуске программа стартует в обычной версии."))
              ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8))
    ver_state = tk.StringVar()
    ttk.Label(ver_tab, textvariable=ver_state, font=("TkDefaultFont", 10, "bold")).grid(
        row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))
    card_n = ttk.LabelFrame(ver_tab, text="Portabilizer")
    card_r = ttk.LabelFrame(ver_tab, text=tr("Portabilizer (R) - радикальный"))
    card_n.grid(row=2, column=0, sticky="nsew", padx=(12, 6), pady=4)
    card_r.grid(row=2, column=1, sticky="nsew", padx=(6, 12), pady=4)
    ver_tab.grid_rowconfigure(2, weight=1)
    ttk.Label(card_n, wraplength=380, justify="left", text=(
        tr("Безопасная версия.\n\n"
        "Исходный файл (установщик, пакет или архив) остаётся нетронутым, рядом создаётся "
        "портативная папка.\n\n"
        "Минус: на диске остаются обе копии: и исходник, и портативная папка.\n\n"
        "Подходит почти для всего, особенно если вы не уверены, что программа заработает."))
              ).pack(anchor="w", padx=10, pady=10)
    ttk.Label(card_r, wraplength=380, justify="left", style="Danger.TLabel", text=(
        tr("Радикальная версия (риск).\n\n"
        "После успешной сборки УДАЛЯЕТ исходный файл (все тома архива) и временные копии, "
        "поэтому итог занимает меньше места. Портативная папка создаётся рядом с исходником.\n\n"
        "Важно: пока идёт работа, места нужно столько же, как в обычной версии: исходник "
        "удаляется только в самом конце, после проверки. Вернуть удалённый файл нельзя: если "
        "что-то пойдёт не так позже, его придётся скачивать или ставить с платформы заново.\n\n"
        "Перед каждым запуском программа просит подтверждение."))
              ).pack(anchor="w", padx=10, pady=10)
    upd_var = tk.BooleanVar(value=bool(settings.get("check_updates", True)))
    upd_state = {"res": None, "done": True, "manual": False}

    def start_update_check(manual=False):
        if not upd_state["done"]:
            return
        upd_state.update(res=None, done=False, manual=manual)

        def work():
            upd_state["res"] = check_update()
            upd_state["done"] = True
        threading.Thread(target=work, daemon=True).start()
        root.after(800, poll_update)

    def poll_update():
        if not upd_state["done"]:
            root.after(800, poll_update)
            return
        r = upd_state["res"]
        if r:
            advisor.add("info", tr("Доступна новая версия Portabilizer: {0}. Скачать её можно в Portabilizer Launcher или на странице {1}.", r['tag'], r['page'] or UPDATE_URL),
                        key="update", cooldown=0)
            if upd_state["manual"]:
                status_var.set(tr("Доступна новая версия: {0}.", r['tag']))
        elif upd_state["manual"]:
            status_var.set(tr("У вас последняя версия ({0}) или нет связи с GitHub.", APP_VERSION))

    def upd_changed(*_a):
        settings["check_updates"] = bool(upd_var.get())
        save_settings(settings)

    upd_var.trace_add("write", upd_changed)
    ttk.Label(ver_tab, text=tr("Версия программы: {0}", APP_VERSION), style="Muted.TLabel").grid(
        row=3, column=0, sticky="w", padx=12, pady=(10, 0))
    ttk.Checkbutton(ver_tab, text=tr("Проверять наличие новых версий при запуске (запрос к GitHub, "
                                  "никакие данные не отправляются)"), variable=upd_var).grid(
        row=4, column=0, columnspan=2, sticky="w", padx=12, pady=(4, 0))
    ttk.Button(ver_tab, text=tr("Проверить сейчас"), command=lambda: start_update_check(True)).grid(
        row=5, column=0, sticky="w", padx=12, pady=8)
    btn_ver_n = ttk.Button(card_n, text=tr("Включить обычную версию"))
    btn_ver_r = ttk.Button(card_r, text=tr("Включить версию (R)"))
    btn_ver_n.pack(padx=10, pady=(0, 10))
    btn_ver_r.pack(padx=10, pady=(0, 10))
    R_HINT = (tr("РЕЖИМ (R): обычный exe просто ПЕРЕНОСИТСЯ в папку App (копии нет, место не нужно). "
              "Архивы и установщики сначала распаковываются, и только потом исходник удаляется: "
              "на время работы нужно место под распакованное. Перед стартом будет подтверждение."))

    # --------------------------------------------------------- вкладка «Оформление»
    themes = load_themes()
    style = ttk.Style(root)
    native_theme = style.theme_use()
    default_bg = root.cget("bg")
    text_defaults = {k: box.cget(k) for k in ("bg", "fg", "insertbackground", "selectbackground",
                                              "selectforeground", "highlightthickness",
                                              "highlightbackground", "highlightcolor")}
    cur = {"theme": None, "dark_sys": None}

    def apply_theme():
        t = pick_theme(settings, ver["radical"], themes)
        cur["theme"], cur["dark_sys"] = t, system_prefers_dark()
        if t is None:
            style.theme_use(native_theme)
            c = dict(CLASSIC)
            for nm, key in (("Muted.TLabel", "muted"), ("Warn.TLabel", "warn"),
                            ("Danger.TLabel", "danger")):
                style.configure(nm, foreground=c[key])
            root.configure(bg=default_bg)
            tcfg = dict(text_defaults)
        else:
            style.theme_use("clam")
            for nm, conf, mp in ttk_style_spec(t):
                style.configure(nm, **conf)
                if mp:
                    style.map(nm, **mp)
            c = t
            root.configure(bg=t["bg"])
            tcfg = dict(bg=t["surface"], fg=t["fg"], insertbackground=t["fg"],
                        selectbackground=t["sel_bg"], selectforeground=t["sel_fg"],
                        highlightthickness=1, highlightbackground=t["border"],
                        highlightcolor=t["accent"])
            root.option_add("*TCombobox*Listbox.background", t["surface"])
            root.option_add("*TCombobox*Listbox.foreground", t["fg"])
            root.option_add("*TCombobox*Listbox.selectBackground", t["sel_bg"])
            root.option_add("*TCombobox*Listbox.selectForeground", t["sel_fg"])
            root.option_add("*Toplevel.background", t["bg"])
            for cb in combos:                   # выпадающий список уже мог быть создан
                try:
                    root.tk.call("ttk::combobox::PopdownWindow", str(cb))
                    lb = f"{cb.tk.call('ttk::combobox::PopdownWindow', str(cb))}.f.l"
                    root.tk.call(lb, "configure", "-background", t["surface"], "-foreground",
                                 t["fg"], "-selectbackground", t["sel_bg"],
                                 "-selectforeground", t["sel_fg"])
                except Exception:
                    pass
        for w in (tips, box):
            w.configure(**tcfg)
        tips.tag_config("info", foreground=c["muted"])
        tips.tag_config("warn", foreground=c["warn"])
        tips.tag_config("danger", foreground=c["danger"])
        tv.tag_configure("done", foreground=c["ok"])
        tv.tag_configure("failed", foreground=c["danger"])
        tv.tag_configure("canceled", foreground=c["warn"])
        tv.tag_configure("interrupted", foreground=c["warn"])
        disks.tag_configure("low", foreground=c["danger"])
        set_dark_titlebar(root, bool(t) and t["kind"] == "dark")
        set_icon(ver["radical"], t is None)
        set_lang_icon(t is None)
        lang_canvas.configure(bg=(t["bg"] if t else default_bg))
        draw_swatches(t)

    look_tab.grid_columnconfigure(1, weight=1)
    ttk.Label(look_tab, wraplength=820, text=(
        tr("Внешний вид окна. Изменения применяются сразу и запоминаются. Красные темы автоматически "
        "включаются в версии (R) и подбираются под светлую или тёмную тему."))
              ).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(12, 10))
    ap_var, dr_var, lr_var = tk.StringVar(), tk.StringVar(), tk.StringVar()

    def ap_choices():
        d = dict((trx(v), k) for k, v in APPEARANCES.items())
        for tid, t in themes.items():
            if not t.get("r") and t.get("user"):
                d[trx(t["name"]) + tr(" (своя)")] = tid
        return d

    def r_choices(kind):
        return {trx(t["name"]) + (tr(" (своя)") if t.get("user") else ""): tid for tid, t in themes.items()
                if t.get("r") and t["kind"] == kind}

    def sync_look_vars():
        ac = ap_choices()
        ap_var.set(next((n for n, k in ac.items() if k == settings.get("appearance", "auto")),
                        trx(APPEARANCES["auto"])))
        for var, kind, key, dflt in ((dr_var, "dark", "dark_r", "dark_r_charcoal"),
                                     (lr_var, "light", "light_r", "light_r")):
            ch = r_choices(kind)
            var.set(next((n for n, k in ch.items() if k == settings.get(key, dflt)),
                         next(iter(ch), "")))

    rows = [(tr("Тема:"), ap_var, ap_choices), (tr("Тёмная красная (R):"), dr_var, lambda: r_choices("dark")),
            (tr("Светлая красная (R):"), lr_var, lambda: r_choices("light"))]
    look_combos = []
    for i, (lab, var, getter) in enumerate(rows, start=1):
        ttk.Label(look_tab, text=lab).grid(row=i, column=0, sticky="w", padx=12, pady=6)
        cb = ttk.Combobox(look_tab, textvariable=var, state="readonly", width=38,
                          values=list(getter()))
        cb.grid(row=i, column=1, sticky="w", padx=4)
        look_combos.append((cb, var, getter))
        combos.append(cb)

    def on_look_change(_e=None):
        settings["appearance"] = ap_choices().get(ap_var.get(), "auto")
        settings["dark_r"] = r_choices("dark").get(dr_var.get(), "dark_r_charcoal")
        settings["light_r"] = r_choices("light").get(lr_var.get(), "light_r")
        save_settings(settings)
        apply_theme()

    for cb, _v, _g in look_combos:
        cb.bind("<<ComboboxSelected>>", on_look_change)

    sw_frame = ttk.Frame(look_tab)
    sw_frame.grid(row=4, column=0, columnspan=3, sticky="w", padx=12, pady=(14, 6))
    sw_cap = ttk.Label(look_tab, style="Muted.TLabel")
    sw_cap.grid(row=5, column=0, columnspan=3, sticky="w", padx=12)

    def draw_swatches(t):
        for w in sw_frame.winfo_children():
            w.destroy()
        if t is None:
            sw_cap.config(text=tr("Классический вид: цвета задаёт Windows."))
            return
        for role in ("bg", "surface", "surface2", "fg", "muted", "accent", "ok", "warn", "danger"):
            tk.Frame(sw_frame, width=34, height=22, bg=t[role], highlightthickness=1,
                     highlightbackground=t["border"]).pack(side="left", padx=2)
        sw_cap.config(text=tr("Сейчас: ") + trx(t["name"]) + tr(". Цвета: фон, поля, кнопки, текст, "
                      "второстепенный, акцент, успех, предупреждение, ошибка."))

    def open_themes_folder():
        d = app_dir() / "themes"
        try:
            d.mkdir(exist_ok=True)
            ex = d / tr("_пример.json")
            if not ex.exists():
                t = {k: v for k, v in themes["dark_r_charcoal"].items() if k not in ("id", "user")}
                t["name"] = tr("Моя тема")
                ex.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
            if os.name == "nt":
                os.startfile(str(d))        # noqa
        except OSError as e:
            messagebox.showwarning("Portabilizer", tr("Не удалось открыть папку: {0}", e), parent=root)

    def reload_themes():
        themes.clear()
        themes.update(load_themes())
        for cb, var, getter in look_combos:
            cb.config(values=list(getter()))
        sync_look_vars()
        on_look_change()

    def pick_my_color():
        from tkinter import colorchooser
        base = cur["theme"] or themes["light"]
        res = colorchooser.askcolor(color=base["accent"], title=tr("Главный цвет (кнопки, прогресс)"),
                                    parent=root)
        if not res or not res[1]:
            return
        accent = res[1]
        tint = None
        if messagebox.askyesno(tr("Свой цвет"), tr("Подкрасить в этот цвет и фон окна?\n\nДа - фон "
                               "получит лёгкий оттенок выбранного цвета.\nНет - фон останется "
                               "нейтральным, цвет будет только у кнопок и акцентов."), parent=root):
            tint = accent
        else:
            tint = "#808080"
        kind = base["kind"]
        try:
            t = make_theme_from_color(accent, kind, bg_tint=tint, name=tr("Мой цвет"))
        except ValueError as e:
            messagebox.showwarning(tr("Свой цвет"), str(e), parent=root)
            return
        d = app_dir() / "themes"
        try:
            d.mkdir(exist_ok=True)
            (d / "my_color.json").write_text(json.dumps(t, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
        except OSError as e:
            messagebox.showwarning(tr("Свой цвет"), tr("Не удалось сохранить тему: {0}", e), parent=root)
            return
        themes.clear()
        themes.update(load_themes())
        for cb, var, getter in look_combos:
            cb.config(values=list(getter()))
        settings["appearance"] = "my_color"
        save_settings(settings)
        sync_look_vars()
        apply_theme()

    bt = ttk.Frame(look_tab)
    bt.grid(row=6, column=0, columnspan=3, sticky="w", padx=12, pady=(14, 4))
    ttk.Button(bt, text=tr("Выбрать свой цвет..."), style="Accent.TButton",
               command=pick_my_color).pack(side="left", padx=(0, 8))
    ttk.Button(bt, text=tr("Открыть папку themes"), command=open_themes_folder).pack(side="left")
    ttk.Button(bt, text=tr("Обновить список тем"), command=reload_themes).pack(side="left", padx=8)
    ttk.Label(look_tab, wraplength=820, style="Muted.TLabel", text=(
        tr("Свои темы: положите файл .json в папку themes рядом с программой (образец "
        "_пример.json создаётся кнопкой выше). В нём цвета в виде #rrggbb, название, "
        "\"kind\": \"light\" или \"dark\" и \"r\": true для красных тем режима R. Недостающие "
        "цвета берутся из встроенной темы. Окна-подтверждения (сообщения Windows) остаются "
        "системными."))).grid(row=7, column=0, columnspan=3, sticky="w", padx=12, pady=(6, 0))
    sync_look_vars()

    def poll_system_theme():
        if settings.get("appearance", "auto") == "auto" and system_prefers_dark() != cur["dark_sys"]:
            apply_theme()
        root.after(3000, poll_system_theme)

    def apply_version():
        r = ver["radical"]
        root.title(tr("Portabilizer (R) - радикальный режим") if r else "Portabilizer")
        btn_start.config(text=tr("Сделать портативным (R)") if r else tr("Сделать портативным"))
        hint_lbl.config(text=R_HINT if r else hint, style="Danger.TLabel" if r else "Muted.TLabel")
        ver_state.set(tr("Сейчас включена: Portabilizer (R) - радикальный") if r
                      else tr("Сейчас включена: Portabilizer (обычная версия)"))
        btn_ver_n.state(["!disabled"] if r else ["disabled"])
        btn_ver_r.state(["disabled"] if r else ["!disabled"])
        apply_theme()

    def set_version(radical):
        if state["job"]:
            messagebox.showinfo("Portabilizer", tr("Переключить версию можно после окончания "
                                "текущей задачи."), parent=root)
            return
        ver["radical"] = bool(radical)
        apply_version()

    btn_ver_n.config(command=lambda: set_version(False))
    btn_ver_r.config(command=lambda: set_version(True))

    # --------------------------------------------------------------- вкладка «Образ ISO»
    # Старые игры проверяют, что в приводе лежит диск с нужной меткой. Образ ISO, подключённый средствами
    # Windows, выглядит как такой привод. Здесь образ собирается из папки с файлами диска.
    iso_src, iso_label, iso_out = tk.StringVar(), tk.StringVar(), tk.StringVar()
    iso_status = tk.StringVar(value=tr("Готов к работе."))
    iso_state = {"stop": False, "busy": False}
    iso_tab.grid_columnconfigure(1, weight=1)

    def iso_row(r, label, var, cmd):
        ttk.Label(iso_tab, text=label).grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(iso_tab, textvariable=var, width=60).grid(row=r, column=1, padx=4, sticky="ew")
        if cmd:
            ttk.Button(iso_tab, text="...", width=4, command=cmd).grid(row=r, column=2, padx=4)

    def iso_pick_src():
        d = filedialog.askdirectory()
        if not d:
            return
        iso_src.set(d)
        if not iso_label.get().strip():
            iso_label.set(re.sub(r"[^A-Za-z0-9_]", "_", Path(d).name).upper()[:32])
        if not iso_out.get().strip():
            iso_out.set(str(Path(d).with_suffix(".iso")) if Path(d).suffix == "" else str(Path(d)) + ".iso")

    def iso_pick_out():
        f = filedialog.asksaveasfilename(defaultextension=".iso", filetypes=[(tr("Образ диска"), "*.iso")],
                                         initialfile=Path(iso_out.get() or "disc.iso").name)
        if f:
            iso_out.set(f)

    iso_row(0, tr("Папка с файлами диска:"), iso_src, iso_pick_src)
    iso_row(1, tr("Метка тома:"), iso_label, None)
    iso_row(2, tr("Файл образа:"), iso_out, iso_pick_out)
    ttk.Label(iso_tab, style="Muted.TLabel", wraplength=820, text=tr(
        "Метка тома должна совпадать с той, что ждёт программа (например, TRAOD1). Готовый образ подключается "
        "правой кнопкой: Подключить (Windows 10 и 11), он появится как DVD-привод с этой меткой.")).grid(
        row=3, column=0, columnspan=3, sticky="w", padx=8, pady=(2, 8))
    iso_btns = ttk.Frame(iso_tab)
    iso_btns.grid(row=4, column=0, columnspan=3, pady=6)
    iso_go = ttk.Button(iso_btns, text=tr("Создать ISO"))
    iso_cancel = ttk.Button(iso_btns, text=tr("Прервать"), state="disabled")
    iso_go.pack(side="left", padx=4)
    iso_cancel.pack(side="left", padx=4)
    iso_pb = ttk.Progressbar(iso_tab, mode="determinate", maximum=100)
    iso_pb.grid(row=5, column=0, columnspan=3, sticky="ew", padx=8, pady=(8, 2))
    ttk.Label(iso_tab, textvariable=iso_status).grid(row=6, column=0, columnspan=3, sticky="w", padx=8)

    def iso_finish(ok, text):
        iso_state["busy"] = False
        iso_go.config(state="normal")
        iso_cancel.config(state="disabled")
        if ok:
            iso_pb["value"] = 100
        iso_status.set(text)

    def iso_start():
        if iso_state["busy"]:
            return
        src_dir, label, out = iso_src.get().strip(), iso_label.get().strip(), iso_out.get().strip()
        if not src_dir or not Path(src_dir).is_dir():
            messagebox.showinfo(tr("Образ ISO"), tr("Выберите папку с файлами диска."), parent=root)
            return
        if not label or len(label) > 32:
            messagebox.showinfo(tr("Образ ISO"), tr("Метка тома должна быть от 1 до 32 символов."), parent=root)
            return
        if not out:
            messagebox.showinfo(tr("Образ ISO"), tr("Укажите, куда сохранить образ."), parent=root)
            return
        if Path(out).exists() and not messagebox.askyesno(
                tr("Образ ISO"), tr("Файл уже есть:\n{0}\n\nЗаменить его?", out), parent=root, default="no"):
            return
        iso_state.update(busy=True, stop=False)
        iso_go.config(state="disabled")
        iso_cancel.config(state="normal")
        iso_pb["value"] = 0
        iso_status.set(tr("Собираю образ..."))
        log(f"ISO: собираю {out} из {src_dir}, метка {label}")

        def progress(done, total):
            pct = int(100 * done / total) if total else 100
            root.after(0, lambda: (iso_pb.configure(value=pct),
                                   iso_status.set(tr("Собираю образ... {0}%", pct))))

        def work():
            try:
                size = build_iso(src_dir, out, label, progress, should_stop=lambda: iso_state["stop"])
            except IsoError as e:
                log(f"ISO: {e}")
                msg = str(e)
                root.after(0, lambda: iso_finish(False, tr("Образ не создан.") if iso_state["stop"] else msg))
                return
            except OSError as e:
                log(f"ISO: ошибка записи: {e}")
                msg = str(e)
                root.after(0, lambda: iso_finish(False, msg))
                return
            log(f"ISO: готово, {fmt_size(size)}")
            root.after(0, lambda: iso_finish(True, tr("Готово: {0} ({1})", out, fmt_size(size))))
        threading.Thread(target=work, daemon=True).start()

    iso_go.config(command=iso_start)
    iso_cancel.config(command=lambda: iso_state.update(stop=True))

    # --------------------------------------------------------------- завершение
    # --- Язык: как в Windows - сверху название на самом языке, под ним оно же на языке интерфейса
    lang_var = tk.StringVar(value=get_lang())
    ttk.Label(lang_tab, text=tr("Язык интерфейса:")).pack(anchor="w", padx=12, pady=(12, 2))
    ttk.Label(lang_tab, style="Muted.TLabel", wraplength=820, text=tr(
        "Язык меняется сразу: окно перезапустится само, настройки сохранятся.")).pack(
        anchor="w", padx=12, pady=(0, 6))
    lang_box = ttk.Frame(lang_tab)
    lang_box.pack(fill="both", expand=True, padx=(12, 0), pady=(0, 10))
    lang_canvas = tk.Canvas(lang_box, highlightthickness=0, bd=0)
    lang_sb = ttk.Scrollbar(lang_box, orient="vertical", command=lang_canvas.yview)
    lang_canvas.configure(yscrollcommand=lang_sb.set)
    lang_sb.pack(side="right", fill="y")
    lang_canvas.pack(side="left", fill="both", expand=True)
    lang_inner = ttk.Frame(lang_canvas)
    lang_win = lang_canvas.create_window((0, 0), window=lang_inner, anchor="nw")
    lang_inner.bind("<Configure>", lambda _e: lang_canvas.configure(scrollregion=lang_canvas.bbox("all")))
    lang_canvas.bind("<Configure>", lambda e: lang_canvas.itemconfigure(lang_win, width=e.width))
    lang_canvas.bind("<Enter>", lambda _e: lang_canvas.bind_all(
        "<MouseWheel>", lambda ev: lang_canvas.yview_scroll(-1 if ev.delta > 0 else 1, "units")))
    lang_canvas.bind("<Leave>", lambda _e: lang_canvas.unbind_all("<MouseWheel>"))
    for code, native in LANGS:
        picked = code == get_lang()
        row_f = ttk.Frame(lang_inner, padding=(4, 5))
        row_f.pack(fill="x")
        top = ttk.Label(row_f, text=native, style="Accent.TLabel" if picked else "TLabel")
        top.pack(anchor="w")
        here = lang_name(get_lang(), code)
        labels = [row_f, top]
        if here != native:
            sub = ttk.Label(row_f, text=here, style="Muted.TLabel")
            sub.pack(anchor="w")
            labels.append(sub)
        if picked:
            ttk.Label(row_f, text="✓", style="Accent.TLabel").place(relx=1.0, x=-14, rely=0.5, anchor="e")
        for w in labels:
            w.bind("<Button-1>", lambda _e, c=code: lang_var.set(c))
            w.configure(cursor="hand2")
        ttk.Separator(lang_inner).pack(fill="x")

    def change_language(*_a):
        code = lang_var.get()
        if code == get_lang():
            return
        if state["job"]:
            messagebox.showinfo(tr("Язык"), tr("Сначала дождитесь конца задачи или прервите её: "
                                              "после смены языка окно перезапускается."), parent=root)
            lang_var.set(get_lang())
            return
        settings["language"] = code
        save_settings(settings)
        RESTART.update(flag=True, geometry=root.geometry(), radical=ver["radical"])
        root.destroy()

    lang_var.trace_add("write", change_language)

    def set_lang_icon(classic):
        try:
            img = tk.PhotoImage(data=GLOBE["pixel" if classic else "smooth"])
            icon_refs["globe"] = img
            nb.tab(lang_tab, image=img, compound="left")
        except Exception:
            pass

    def on_close():
        job = state["job"]
        if job:
            if not messagebox.askyesno(tr("Идёт работа"), tr("Задача ещё выполняется. Прервать её и выйти?"),
                                       icon="warning", parent=root):
                return
            job.cancel()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(500, tick)
    root.after(800, update_diag)
    root.after(3000, poll_system_theme)
    if settings.get("check_updates", True):
        root.after(2500, start_update_check)
    apply_version()
    if start_radical:
        set_version(True)

    if _hook:       # для автотестов: передаём управление, окно не запускаем
        _hook({"lang_var": lang_var, "settings": settings, "ver": ver, "root": root, "go": go, "src": src, "dst": dst, "mode_var": mode_var,
               "history": history, "advisor": advisor, "state": state, "log": log,
               "refresh_history": refresh_history, "tv": tv, "update_diag": update_diag,
               "tick": tick, "set_buttons": set_buttons, "do_pause": do_pause,
               "do_resume": do_resume, "pb": pb, "status_var": status_var, "box": box,
               "on_job_event": on_job_event, "retry": retry, "show_low_space": show_low_space,
               "choose_exe_ui": choose_exe_ui, "chooser_dlg": chooser_dlg,
               "low_dlg": low_dlg, "do_cancel": do_cancel,
               "open_result": open_result, "launch_result": launch_result, "make_shortcut": make_shortcut,
               "delete_portable": delete_portable, "delete_source": delete_source,
               "forget": forget, "nb": nb, "disks": disks, "cpu_var": cpu_var,
               "sysinfo": sysinfo, "tips": tips, "ver": ver, "set_version": set_version,
               "btn_start": btn_start, "hint_lbl": hint_lbl, "ver_state": ver_state,
               "icon_refs": icon_refs, "btn_ver_n": btn_ver_n, "btn_ver_r": btn_ver_r,
               "ver_tab": ver_tab, "apply_theme": apply_theme, "settings": settings, "start_update_check": start_update_check,
               "upd_state": upd_state, "poll_update": poll_update,
               "themes": themes, "style": style, "theme_cur": cur, "look_tab": look_tab,
               "on_look_change": on_look_change, "ap_var": ap_var})
        return
    root.mainloop()


def cli(argv):
    pos, opts = [], {}
    for a in argv:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            opts[k.lower()] = v
        elif a.startswith("--"):
            opts[a[2:].lower()] = "1"
        else:
            pos.append(a)
    if not pos:
        print(__doc__)
        return 1
    out = pos[1] if len(pos) > 1 else "."
    mode = opts.get("mode", "auto")
    RUN_POLICY["value"] = opts.get("run", "auto").lower()
    if RUN_POLICY["value"] not in RUN_POLICIES:
        print("--run принимает: auto, noadmin, admin")
        return 1
    log = make_logger(print)
    radical = "radical" in opts
    if radical and "yes" not in opts:
        print("Радикальный режим УДАЛЯЕТ исходный файл после успешной сборки (вернуть его нельзя).\n"
              "Если вы уверены, добавьте --yes. Ничего не сделано.")
        return 1

    if mode != "launcher" and Path(pos[0]).is_file():
        pre = preflight(Path(pos[0]), Path(out), mode)
        if pre["level"] != "ok":
            print(("ВНИМАНИЕ: " if pre["level"] == "warn" else "ОПАСНО: ") + pre["text"])
            if pre["level"] == "danger" and "force" not in opts:
                print("Остановлено. Освободите место, выберите другой диск или добавьте --force.")
                return 1

    job = Job(auto_cancel_on_low_space=True, on_event=lambda kind, text: print(
        text + " Работа остановлена, чтобы не забить диск."))

    def ticker():
        last = -1
        while not job.finished:
            p = job.progress
            if p is not None and p // 10 != last:
                last = p // 10
                print(f"  ... {p}%")
            time.sleep(1)
    threading.Thread(target=ticker, daemon=True).start()
    history = History()
    dxo = opts.get("dx", "install").lower()
    if dxo not in ("install", "skip", "cancel"):
        print("--dx принимает: install, skip, cancel")
        return 1
    ok = portabilize(pos[0], out, log, mode, opts.get("exe", ""), job=job, history=history,
                     radical=radical, confirmed=radical and "yes" in opts,
                     dx_prompt=lambda text: dxo)
    return 0 if ok else 1


def attach_console():
    """В собранном окне без консоли (--windowed) подключаем вывод к консоли, откуда запустили."""
    if os.name != "nt":
        return
    try:
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):         # ATTACH_PARENT_PROCESS
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
            sys.stderr = sys.stdout
    except Exception:
        pass


def run_gui(start_radical=False):
    """Открывает окно; смена языка закрывает его и открывает заново (версия R сохраняется)."""
    RESTART["radical"] = start_radical
    while True:
        RESTART["flag"] = False
        gui(start_radical=RESTART["radical"])
        if not RESTART["flag"]:
            break


if __name__ == "__main__":
    args = sys.argv[1:]
    if [a.lower() for a in args] == ["--r"]:      # ярлык «Portabilizer (R)»: окно сразу в версии R
        run_gui(start_radical=True)
    elif args:
        attach_console()
        sys.exit(cli(args))
    else:
        run_gui()
