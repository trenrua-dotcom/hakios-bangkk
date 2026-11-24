#!/usr/bin/env python3
"""Extract flattened device trees from an Android vendor_boot image (Windows friendly).

usage: python tools/extract-vendor-dtb.py vendor_boot.img [--out DIR]

Supports Android vendor_boot header versions 3 and 4. The DTB section can contain
more than one concatenated FDT; each is written separately so soc-args.py can read it.
"""
import argparse
import importlib.util
import os
import struct
import sys

MAGIC = b'VNDRBOOT'
FDT_MAGIC = b'\xd0\x0d\xfe\xed'


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def align(value, boundary):
    return (value + boundary - 1) // boundary * boundary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vendor_boot')
    parser.add_argument('--out', default='bangkk-dtb')
    args = parser.parse_args()

    data = open(args.vendor_boot, 'rb').read()
    if data[:8] != MAGIC or len(data) < 2112:
        sys.exit('extract-vendor-dtb: not an Android vendor_boot image')

    version = u32(data, 8)
    if version not in (3, 4):
        sys.exit(f'extract-vendor-dtb: unsupported vendor_boot header version {version}; expected 3 or 4')
    page_size = u32(data, 12)
    ramdisk_size = u32(data, 24)
    header_size = u32(data, 2096)
    dtb_size = u32(data, 2100)
    if page_size < 512 or page_size > 65536 or page_size & (page_size - 1):
        sys.exit(f'extract-vendor-dtb: invalid page size {page_size}')
    minimum_header = 2112 if version == 3 else 2128
    if header_size < minimum_header or header_size > page_size:
        sys.exit(f'extract-vendor-dtb: invalid header size {header_size} for version {version}')
    if not dtb_size:
        sys.exit('extract-vendor-dtb: vendor_boot contains no DTB section')

    dtb_offset = align(header_size, page_size) + align(ramdisk_size, page_size)
    dtb_end = dtb_offset + dtb_size
    if dtb_end > len(data):
        sys.exit(f'extract-vendor-dtb: truncated DTB section ({dtb_offset:#x}..{dtb_end:#x}, image is {len(data):#x})')
    section = data[dtb_offset:dtb_end]

    trees = []
    cursor = 0
    while True:
        start = section.find(FDT_MAGIC, cursor)
        if start < 0:
            break
        if start + 8 > len(section):
            break
        size = struct.unpack_from('>I', section, start + 4)[0]
        end = start + size
        if size < 40 or end > len(section):
            cursor = start + 4
            continue
        trees.append((start, section[start:end]))
        cursor = align(end, 4)

    if not trees:
        sys.exit('extract-vendor-dtb: no flattened-tree (FDT) magic in the vendor_boot DTB section')

    os.makedirs(args.out, exist_ok=True)
    spec = importlib.util.spec_from_file_location('hakios_soc_args', os.path.join(os.path.dirname(__file__), 'soc-args.py'))
    soc_args = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(soc_args)
    for index, (offset, tree) in enumerate(trees):
        path = os.path.join(args.out, f'dtb-{index:02d}.dtb')
        with open(path, 'wb') as output:
            output.write(tree)
        root = soc_args.nodes_of(tree).get('', {})
        model = root.get('model', b'').split(b'\0')[0].decode(errors='replace')
        compatible = ','.join(value.decode(errors='replace') for value in root.get('compatible', b'').split(b'\0') if value)
        print(f'{path}: {len(tree)} bytes, model={model!r}, compatible={compatible!r}, section offset {offset:#x}')

    print(f'extract-vendor-dtb: header v{version}, page {page_size}, found {len(trees)} FDT(s)')


if __name__ == '__main__':
    main()
