# -*- mode: python -*-
from __future__ import print_function  # isort:skip
import os
import platform
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

from rotkehlchen.constants.misc import GLOBALDB_NAME
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.types import EVM_CHAINS_WITH_TRANSACTIONS, Location
from rotkehlchen.utils.misc import get_system_spec

"""
PyInstaller spec file to build single file or dir distributions
"""

# Set to false to produce an exploded single-dir
ONEFILE = int(os.environ.get('ONEFILE', True))
MACOS_IDENTITY = os.environ.get('IDENTITY', None)


def Entrypoint(dist, group, name, scripts=None, pathex=None, hiddenimports=None, hookspath=None, excludes=None, runtime_hooks=None, datas=None):  # noqa: E501
    scripts = scripts or []
    pathex = pathex or []
    # insert path of the egg at the verify front of the search path
    pathex = [Path.cwd()] + pathex
    # script name must not be a valid module name to avoid name clashes on import
    script_path = os.path.join(workpath, name + '-script.py')
    with open(script_path, 'w') as fh:
        fh.write('import rotkehlchen.__main__\n')
        fh.write('rotkehlchen.__main__.main()')

    return Analysis(
        [script_path] + scripts,
        pathex=pathex,
        hiddenimports=hiddenimports,
        hookspath=hookspath,
        excludes=excludes,
        runtime_hooks=runtime_hooks,
        datas=datas,
    )

# We don't need Tk and friends
sys.modules['FixTk'] = None

if (platform_name := platform.system().lower()) == 'darwin':
    platform_name = f"macos-{'arm64' if platform.machine() == 'arm64' else 'x64'}"

executable_name = 'rotki-core-{}-{}'.format(
    get_system_spec()['rotkehlchen'],
    platform_name,
)

hiddenimports = ['cytoolz.utils', 'cytoolz._signatures', 'coincurve._cffi_backend']
# Since the exchanges are loaded dynamically and some of them may not be detected
# by pyinstaller (https://github.com/rotki/rotki/issues/602) make sure they are
# all included as imports in the created executable
for exchange_name in SUPPORTED_EXCHANGES:
    if exchange_name == Location.BINANCEUS:
        continue
    hiddenimports.append(f'rotkehlchen.exchanges.{exchange_name}')

for chain in EVM_CHAINS_WITH_TRANSACTIONS:  # load modules from the evm chains
    hiddenimports.extend(collect_submodules(f'rotkehlchen.chain.{chain.name.lower()}.modules'))

a = Entrypoint(
    'rotkehlchen',
    'console_scripts',
    'rotkehlchen',
    hookspath=['tools/pyinstaller_hooks'],
    hiddenimports=hiddenimports,
    datas=[
        # This list should be kept in sync with setup.py (package_data)
        ('rotkehlchen/data/eth_abi.json', 'rotkehlchen/data'),
        ('rotkehlchen/data/eth_contracts.json', 'rotkehlchen/data'),
        (f'rotkehlchen/data/{GLOBALDB_NAME}', 'rotkehlchen/data'),
        ('rotkehlchen/data/globaldb_v2_v3_assets.sql', 'rotkehlchen/data'),
        ('rotkehlchen/data/nodes.json', 'rotkehlchen/data'),
        ('rotkehlchen/data/nodes_as_of_1-26-1.json', 'rotkehlchen/data'),
        ('rotkehlchen/data/populate_asset_collections.sql', 'rotkehlchen/data'),
        ('rotkehlchen/data/populate_multiasset_mappings.sql', 'rotkehlchen/data'),
        ('rotkehlchen/data/populate_location_asset_mappings.sql', 'rotkehlchen/data'),
        ('rotkehlchen/data/populate_location_unsupported_assets.sql', 'rotkehlchen/data'),
        # TODO
        # We probably should have a better way to specify some data should be loaded
        # by a module in pyinstaller. Should be loaded dynamically by rotki and not
        # by pyinstaller if we want it to be truly modular
        (
            'rotkehlchen/chain/ethereum/modules/dxdaomesa/data/contracts.json',
            'rotkehlchen/chain/ethereum/modules/dxdaomesa/data',
        ),
    ],
    excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'debugimporter'],
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        name=executable_name,
        debug=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,
        console=True,
    )
else:

    identity = None
    entitlements = None
    if MACOS_IDENTITY is not None:
        identity = MACOS_IDENTITY
        entitlements = 'packaging/entitlements.plist'

    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name=executable_name,
        debug=False,
        strip=False,
        upx=False,
        console=True,
        codesign_identity=identity,
        entitlements_file=entitlements,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name='rotki-core',
        codesign_identity=identity,
        entitlements_file=entitlements,
    )
