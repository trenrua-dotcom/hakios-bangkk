# Moto G84 5G (`bangkk`)

Initial HakiOS device definition for the Moto G84 5G. The connected phone reported
`motorola/bangkk_g/bangkk:15/V1TCS35H.88-20-1-6-8/441cd-4bd9a2:user/release-keys`.

## Device tree evidence

The supplied stock `vendor_boot.img` is Android vendor boot header v3. Its first
DTB is 323,756 bytes and reports:

- `model`: `Qualcomm Technologies, Inc. Blair`
- `compatible`: `qcom,blair`

The tree identifies the Qualcomm Blair platform, while the phone fingerprint
identifies the board as `bangkk`. The generic DTB model does not by itself
confirm board-specific display, memory, or UEFI settings. The source image and
extracted DTB are intentionally not committed; `soc.args` records the values
read from the supplied DTB.

The public [LineageOS device record](https://github.com/LineageOS/lineage_wiki/blob/main/_data/devices/bangkk.yml)
lists eight Kryo 660 CPU cores, Adreno 619, and UFS 2.2 storage. The public
[bangkk Android device tree](https://github.com/Motorola-SM6375-Devs/android_device_motorola_bangkk)
loads both `focaltech_v3` and `goodix_brl_mmi` touch modules; the exact active
panel and touch controller still need to be identified on this unit.

The tree yielded these boot arguments:

| Argument | Value |
|---|---|
| `soc_ipa_base` | `0x5840000` |
| `soc_gsi_base` | `0x5804000` |
| `soc_ipcc` | `0x208000` |
| `soc_apps_smmu` | `0xc600000` |
| `modem_ipa_fw_at` | `0x8aa10000` |
| `soc_smem` | `0x80900000` |
| `soc_imem` | `0xc000000` |
| `soc_ipa_stream` | `0x4a0` |
| `soc_ipa_stream_uc` | `0x4a2` |
| `soc_pas_mpss` | `0x4` |
| `soc_pas_ipa` | `0xf` |
| `soc_ipa_fw` | `ipa_fws` |

`tools/soc-args.py` did not find `soc_aoss`, `soc_rsc`, `soc_cmd_db`, or
`soc_mpss_mem` in this DTB. These remain unknown; do not infer them from the G85.

## Port status

The G84 and G85 share the SM6375/Blair SoC family. That supports starting with
the G85's SoC-level knowledge, but does not establish that its board firmware,
UEFI addresses, display setup, or peripheral configuration work on the G84.
This device's `sm6375` layer is therefore only a placeholder, and its phone
drivers start disabled in `configs/moto-g84.config`.

Still required before a useful boot attempt:

- Build or obtain a G84-specific `BootShim.bin`, `SILICIUM_UEFI.fd`, ramdisk,
  and `mkbootimg.py`; verify the UEFI load address, size, and Android boot
  header version against that build.
- Identify the G84 panel, touch controller, storage, buttons, and device-tree
  nodes/interrupts; port and enable each driver only after confirming its data.
- Pull the G84's required firmware using the device's own Android firmware
  files. Never substitute G85 board firmware.
- Test first with temporary `fastboot boot`; the Windows packer does not flash
  partitions.

Build settings live in `configs/moto-g84_defconfig` and
`configs/moto-g84.config`. The device is included in the common manifest as a
local path so this port skeleton remains visible in the working checkout.
