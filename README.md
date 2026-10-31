# Portabilizer

Превращает установщик, пакет или архив в портативную папку (`App` + `Data` + `Launch.bat`). Есть радикальный режим R.

**Скачать:** [Releases](../../releases): `Portabilizer.exe` или zip. Удобнее через
[Portabilizer Launcher](https://github.com/Vanyok-gh/Portabilizer-launcher): он показывает версии, описание и ставит их одним нажатием.

## Для автора: как выпустить версию

1. Поднять `APP_VERSION` в `portabilizer_v8.py`, дописать раздел `## vX.Y` в `CHANGELOG.md`.
2. Создать тег `vX.Y` (Releases -> Draft a new release -> новый тег -> Publish, либо `git tag vX.Y && git push --tags`).
3. GitHub сам соберёт `Portabilizer.exe` (`.github/workflows/release-portabilizer.yml`) и создаст релиз с описанием из CHANGELOG.

Локальная сборка: `build.bat`.
