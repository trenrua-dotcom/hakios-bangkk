# HakiOS on a Windows machine

How to build and run HakiOS with a Windows PC and a phone. It works, with each tool where it fits.
Everything here was done on a real machine and phone; `tools/doctor.sh` checks the same things for you.

The instructions below describe the established POCO X5 Pro (`redwood`) workflow. For the experimental Moto G84 (`bangkk`) path
without WSL, see [Moto G84 without WSL](#moto-g84-without-wsl).

## What runs where

| Job | Where | Why |
|---|---|---|
| Build the images (`sysimage/unpack.sh`, `userland/build.sh`) | **WSL 2, in its own filesystem** (`~/hakios`) | `unpack.sh` makes files named `NAME:com.apple.decmpfs`; NTFS forbids `:`. The Windows drive is also slow for tens of thousands of small files. |
| Drive the phone (`./xl`, `tools/modem-cycle-win.sh`) | **Git Bash**, in your Windows checkout | `fastboot` and `adb` are Windows programs that see the phone's USB; WSL 2 does not, without usbipd. |

So: build in WSL, copy `userland/root.apfs` and `userland/system.apfs` to the Windows checkout, run `xl`
from Git Bash.

## Moto G84 without WSL

The XNU and Darwin userland source build in this repository currently targets Linux or macOS; the dependency setup expects
Linux cctools and Unix filesystem behavior. Windows can still package and boot a prebuilt open-kernel image natively, without
WSL, with Python and Android platform-tools:

```powershell
# From the checkout root. First supply the G84-specific UEFI files listed below.
.\tools\build-bangkk.ps1

# Optional: boot it temporarily while the phone is in fastboot mode.
.\tools\build-bangkk.ps1 -Boot
```

This produces `out\hakios-bangkk.img`. `-Boot` uses `fastboot boot`, which runs the image from RAM and does not flash a
partition. The script uses `prebuilt\hakios-kernel` and `prebuilt\userland\hello`; it does not compile XNU or SpringBoard.
For a source build without WSL, run **Actions → Build HakiOS for Moto G84 (bangkk) → Run workflow** on GitHub. Its
`hakios-bangkk` artifact contains the G84 kernel, open loader, hello ramdisk, and XNUP payload. Download and extract it
into the checkout root, preserving its folder structure. Once the G84-specific UEFI files below are available locally, package the Action payload
on Windows with:

```powershell
.\tools\build-bangkk.ps1 -Payload .\out\hakios-bangkk-payload.bin
```

To use a kernel and ramdisk already in `prebuilt\`, omit `-Payload` and the script creates its own payload.

The G84 image requires all of these files in `devices\moto-g84\prebuilt\`:
`BootShim.bin`, `SILICIUM_UEFI.fd`, `device-tree.dtb`, `ramdisk`, and `mkbootimg.py`. They must be built or extracted for the
Moto G84 itself. The supplied stock `vendor_boot.img` yielded a G84 candidate DTB, now kept locally at
`devices\moto-g84\prebuilt\device-tree.dtb`; it identifies the Blair SoC, but has not been validated as the correct
boot-image DTB. The G85 (`malmo`) and G84 (`bangkk`) share an SoC family, but this checkout has no verified G84 UEFI image
or boot parameters. The packer deliberately refuses to substitute a G85 UEFI build. The G84 image's current
`fd_base`, size, and Android boot header version are provisional values copied from G85 and still need verification on a G84.

To extract the DTB from the G84's stock `vendor_boot.img` in Windows, use:

```powershell
python tools\extract-vendor-dtb.py C:\path\to\vendor_boot.img --out work\bangkk-dtb
python tools\soc-args.py work\bangkk-dtb\dtb-00.dtb
```

If it contains several DTBs, the first command prints each one's model and compatible values; run `tools\soc-args.py`
on the candidate identified as `bangkk`.
This reads a local image file and does not write to the phone.

If the G84 bootloader supports the standard read-only `fastboot fetch` command, you can obtain that image from the phone
without downloading the full firmware package. From Android, run `adb reboot bootloader`, read the active slot with
`fastboot getvar current-slot`, then fetch the matching `vendor_boot_a` or `vendor_boot_b` to a local file. Return to Android
with `fastboot reboot`. If `fastboot fetch` reports that the bootloader does not support it, use the matching stock firmware
package instead.

## Setup

1. **Platform-tools:** unpack Google's Android platform-tools to `C:\platform-tools` (adb, fastboot).
   fastboot worked here without a separate USB driver.
2. **WSL 2 Ubuntu:** `sudo apt install 7zip clang lld lz4 python3 git make` (7-Zip must be 23 or newer).
3. **Git Bash** (Git for Windows). Check your Windows checkout and WSL both with:
   ```sh
   tools/doctor.sh           # in Git Bash (host checks for the xl side, and the phone)
   tools/doctor.sh           # in WSL, in ~/hakios (host checks for the build side)
   ```
4. **In Git Bash**, before using `xl`: `export PATH="$PWD/tools/win-bin:/c/platform-tools:$PATH"`.
   `tools/win-bin/flock` replaces util-linux's `flock`, which Git Bash does not have and `xl` needs.

## The phone

- Turn on USB debugging. Unlock the bootloader (yours to do; it wipes the phone).
- **Trust the device tree, not the product name.** Some units report a different brand and model than
  the board they really are (root-hiding modules fake the identity and even the bootloader's
  "locked" state). `tools/doctor.sh` prints both. The supported platform is `redwood` / SM7325.
- **Firmware needs root on some ROMs.** If `devices/redwood/pull-firmware.sh` reports every file
  "not on the phone" but `doctor` says the firmware is readable only by root, use
  `devices/redwood/pull-firmware-root.sh`. It copies under `su` to a staging directory, pulls, and
  removes the staging directory; nothing on the phone is changed.

## Build and run

```sh
# WSL, in ~/hakios (a clone in WSL's own filesystem, with fw-*/ copied in):
sysimage/unpack.sh ~/iPhone10,3,iPhone10,6_16.5_20F66_Restore.ipsw   # your own IPSW, ~5 min
PREBUILT=1 REST=1 MODEM=1 SYSTEM=1 userland/build.sh     # root.apfs + system.apfs, ~4 min, no theos needed
cp userland/root.apfs userland/system.apfs /mnt/d/.../hakios/userland/

# Git Bash, in the Windows checkout:
./xl enter                  # Android -> fastboot -> the loader in RAM (also the unlock test)
./xl screenshot logs/s.png  # what the loader put on the screen
./xl log                    # the loader's log
./xl reload                 # restart the phone and enter the loader again
./xl reboot                 # back to Android
```

Nothing is flashed: everything is booted from RAM, and a reboot brings Android back.

## When something goes wrong

- **`xl state` says `absent`** for more than three minutes: the phone is not on USB at all. Check the
  cable and the screen; hold power about 15 seconds to restart it into Android. `doctor` shows whether
  Windows sees any device.
- **`Failed to mount root device`** from a run: it was started without a root image. A run needs
  `system.apfs` built with `MODEM=1` if it uses the modem (`tools/modem-cycle-win.sh`).
- **`tools/modem-cycle.sh` fails under Git Bash:** use `tools/modem-cycle-win.sh`; the original puts the
  macOS helpers in `tools/macos-bin` first on `PATH`, and they do not run on Windows.

## Metal: a run, measured, from Windows

The window server drawing through Metal (`METAL_PLUGIN=ca`) and the frame-rate bench, with one command in Git Bash. What the two paths
are and what the arguments do: [Metal on the Adreno](reference/metal.md).

The plug-in is compiled, so the build needs the cross toolchain (`xnu-deps/setup.sh`) and `hakios-metal/` of this tree
beside the checkout; `PREBUILT=1` compiles nothing, and `prebuilt/userland` has no plug-in.

```sh
# WSL, in ~/hakios: QuartzCore's library for CoreAnimation, then the image with the Metal plug-in and the bench.
# Off a Mac, name a later CoreAnimation's library to take the rest of its shaders from (a Mac's
# QuartzCore.framework/Versions/A/Resources/default.metallib copied over, or a later system's out of its IPSW):
CA_QC_METALLIB=/mnt/c/.../default.metallib tools/ca-metallib.py ~/ca-share
(cd hakios-metal && make ios MESA=1)
METAL_PLUGIN=ca RC_JOBS=rc.jobs.bench EXTRA_SHARE=~/ca-share REST=1 SYSTEM=1 userland/build.sh
cp userland/root.apfs userland/system.apfs /mnt/d/.../hakios/userland/

# Git Bash, in the Windows checkout (the phone in Android is fine: the script takes it into the loader):
tools/metal-run.sh                       # 180 s; the summary in logs/<time>-metal.txt
MORE="metal_gmem=1" tools/metal-run.sh   # with tiled rendering (each pass left in sysmem says why)
MORE="wallpaper_cache=1" tools/metal-run.sh   # any boot-argument beside the defaults
SHOTS=20 tools/metal-run.sh              # and a screenshot every 20 s, logs/<time>-shots/
```

For UniXNU's Metal on Vulkan, build its pieces in WSL first, then the same image with two more options, and name it at boot. It takes
rustup's cargo with Rust 1.98 and the `aarch64-apple-ios` target, `llvm-as` of LLVM 21, `glslang-tools`, and the theos iPhoneOS 16.5 SDK:

```sh
# WSL, in ~/hakios:
tools/mk-mesa.sh && tools/mk-turnip.sh && tools/mk-m2v.sh
METAL_PLUGIN=ca TURNIP=1 M2V=1 RC_JOBS=rc.jobs.bench EXTRA_SHARE=~/ca-share REST=1 SYSTEM=1 userland/build.sh
cp userland/root.apfs userland/system.apfs /mnt/d/.../hakios/userland/

# Git Bash:
MORE="metal_m2v=1" tools/metal-run.sh
MORE="metal_m2v=1 tu_debug=perf" tools/metal-run.sh   # and Turnip's own account of its render passes
```

The summary's frames per gesture come from `tools/frames.py`, which runs anywhere Python does: `python tools/frames.py logs/last.log`.

`tools/metal-run.sh` keeps `/private/var` between boots by default (`ufs=2 ufs_write=1 var_store=1`, the partition
`darwin` only; `PERSIST=0` for none), so the shader stages the window server compiles are compiled once. To put them
into the image, so that not even the first boot compiles them: with the phone back in Android,

```sh
tools/metal-cache-seed.sh                # reads darwin (read only, adb + root) into userland/hakios-metal-cache
```

and copy `userland/hakios-metal-cache` to WSL's `userland/` before the next `userland/build.sh`.
