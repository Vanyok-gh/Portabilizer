# Disc games -> portable: notes from Tomb Raider: Angel of Darkness (TRAOD)

What we learned making a 2003 disc game run **without the disc, without installing and without admin rights**.
Target: standard Windows 11 user, no admin password.

## Pipeline that worked
1. **Extract the installer without installing** (`msiexec /a setup.msi /qn TARGETDIR="<dir>"`, quotes around the value).
   - InstallShield `setup.exe` contains a `.msi`; the engine (`isscript.msi`) needs admin, so we edit a **temp copy** of the MSI:
     remove actions starting with `IS` from `AdminExecuteSequence`/`AdminUISequence` (PowerShell `WindowsInstaller.Installer` COM).
   - Files that are not in the packages (they sit on disc 2) cause error 1308/1309: read the MSI tables offline (`pzp_msi.py`)
     and delete those `File` rows + null the component `KeyPath`.
   - DirectX9 component (`BDA.cab`) is skipped.
   - Main exe pick must skip helpers like `_ISDel.exe`, `inst32`.
2. **Disc image**: build ISO 9660/Joliet (`pzp_iso.py`) from the folder whose root has `Data` and `Launcher.exe`.
   Volume label must match what the game checks (`TRAOD1`, `TRAOD2`). Mount with Windows' own mounter
   (`Mount-DiskImage`) - works for a standard user. The image file must be outside the source folder.
3. **Working directory** must be the install root (`...\TRAOD`), not `bin`: the game opens `DATA\ACTOR.DB`, `.\cache`.
   Otherwise: `script_mgr.c(400) 'pData && length>0'`.
4. **Registry** (the game reads it, written by the original installer): `SOFTWARE\Core Design\TombRaiderAngelOfDarkness\1.0`
   `InstalledPath` (with trailing `\`), `Language` = dword 1033. The MSI `Registry` table lists exactly these keys.
   HKCU works for the game itself; the original `Launcher.exe` reads HKLM only (exits silently otherwise) - so we bypass it.
5. **Video crash on Win11** `sys_d3d_vmr9.cpp(1568) 'SUCCEEDED(hr)'`: the old overlay-mixer path fails
   (`IMixerPinConfig::SetColorKey`). The launcher normally sets "FMV VMR9" in the per-adapter key
   `HKCU\...\Gfx\FullScreen\<GUID bytes>_w_h` (about 50 values, written by the game itself; not hand-writable).
   Fix: compatibility patch of the user's own exe: at the check
   `8A 90 FB 16 00 00 84 D2 75 08 B8 01 00 00 00 59 5E C3` change `75 08` (jne) -> `EB 08` (jmp).
   Found once each in `TRAOD_P3.exe` and `TRAOD_P4.exe`; not in base `TRAOD.exe` (different build). Original saved as `.bak`.
   Script: `Enable_VMR9.ps1` (verify signature, exactly one match, backup, `-Undo`).
6. **"Unknown file ... insert the correct disc: data\audio\frontend.awd.clz"**: the MSI puts files that belong to
   `CDROM_DATA`, `CDROM_DATA_AUDIO`, `CDROM_DATA_MAPS` (directories directly under `SourceDir`) into `App\Data`,
   but the game looks for them in `TRAOD\data`. Fix: move/merge `App\Data\*` into `TRAOD\data\`.
7. **Launcher script** `Play_TRAOD.bat` + `Play_TRAOD.ps1`: find mounted disc by volume label, else find/ask for ISO and mount it,
   set HKCU keys, start `TRAOD_P4.exe` with working dir = install root, dismount what we mounted. Desktop shortcut via WScript.Shell.

## Not possible / do not try
- Hand-writing the `Gfx\FullScreen\...` key from a friend's `.reg`: key name depends on the adapter GUID.
- Anything that bypasses copy protection, cracks, no-CD patches. Only the user's own legal disc images are used.
  (Patch above is a video-compatibility fix, not DRM.)

## Environment pitfalls
- cmd vs PowerShell quoting; trailing backslash before a quote (`"C:\dir\"`) breaks `reg add` and `-File` arguments.
- ISO from the nested folder (`TRAOD1\TRAOD1`): the volume root must contain `Data\`.
- Several mounted drives with the same label: pick any, the game only checks label/files.
- 32-bit registry virtualization (VirtualStore) did not help.
- Screenshots are saved as `.tga` in `TRAOD\ScreenShots` (auto-convert to PNG was tried and postponed).

## Data still missing in the user's copy (low priority)
`FRONTEND.GMX`/`INVENT.GMX` variants, some Paris maps/audio, `EN_FLASH.MPG` - they come from disc 2 / `Release` folder.

## v10 (implemented in `pzp_disc.py`, called from `digitize_disc_game`)
1. Analyze installer MSI: `Registry` table -> `.reg` (HKLM -> HKCU, `{ROOT}` placeholder), `Media` volume labels,
   directories outside INSTALLDIR (`CDROM_*`) = disc layout -> merge into install `data` by case-insensitive name.
2. Recipes (`recipes/*.json`, key = MSI ProductCode or exe name): exe patches (signature, replace, expected hits),
   preferred exe, disc labels, working dir.
3. Generated `Play` script like the above (disc mount by label, registry, working dir, patches applied once).
4. UI: "disc game" option; log shows what was detected.
