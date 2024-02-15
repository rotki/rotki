#!/usr/bin/env python3
from pathlib import Path

from rotkehlchen.chain.ethereum.defi.protocols import DEFI_PROTOCOLS
from os.path import exists

ROOT_DIR = Path.cwd()
ICON_DIR = ROOT_DIR / "frontend" / "app" / "public" / "assets" / "images" / "protocols"

for protocol in DEFI_PROTOCOLS:
    icon_file = DEFI_PROTOCOLS[protocol].icon
    icon = ICON_DIR / icon_file
    if not exists(icon):
        print(f'icon {icon_file} does not exist in {ICON_DIR}')
        exit(1)

print('All good')
