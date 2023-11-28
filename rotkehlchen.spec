# -*- mode: python -*-
from __future__ import print_function  # isort:skip
import os
import platform
import sys
from distutils.spawn import find_executable

from PyInstaller.utils.hooks import collect_submodules

from rotkehlchen.constants.misc import GLOBALDB_NAME
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import get_system_spec

"""
PyInstaller spec file to build single file or dir distributions

Currently only tested on macOS
"""

# Set to false to produce an exploded single-dir
ONEFILE = int(os.environ.get('ONEFILE', True))
MACOS_BUILD_ARCH = os.environ.get('MACOS_BUILD_ARCH', None)


def Entrypoint(dist, group, name, scripts=None, pathex=None, hiddenimports=None, hookspath=None,
               excludes=None, runtime_hooks=None, datas=None):
    import pkg_resources

    # get toplevel packages of distribution from metadata
    def get_toplevel(dist):
        distribution = pkg_resources.get_distribution(dist)
        if distribution.has_metadata('top_level.txt'):
            return list(distribution.get_metadata('top_level.txt').split())
        else:
            return []

    hiddenimports = hiddenimports or []
    packages = []
    for distribution in hiddenimports:
        try:
            packages += get_toplevel(distribution)
        except:
            pass

    scripts = scripts or []
    pathex = pathex or []
    # get the entry point
    ep = pkg_resources.get_entry_info(dist, group, name)
    # insert path of the egg at the verify front of the search path
    pathex = [ep.dist.location] + pathex
    # script name must not be a valid module name to avoid name clashes on import
    script_path = os.path.join(workpath, name + '-script.py')
    print("creating script for entry point", dist, group, name)
    with open(script_path, 'w') as fh:
        print("import", ep.module_name, file=fh)
        print("%s.%s()" % (ep.module_name, '.'.join(ep.attrs)), file=fh)
        for package in packages:
            print("import", package, file=fh)

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

executable_name = 'rotki-core-{}-{}'.format(
    get_system_spec()['rotkehlchen'],
    'macos' if platform.system() == 'Darwin' else platform.system().lower())

hiddenimports = ['cytoolz.utils', 'cytoolz._signatures']
# Since the exchanges are loaded dynamically and some of them may not be detected
# by pyinstaller (https://github.com/rotki/rotki/issues/602) make sure they are
# all included as imports in the created executable
for exchange_name in SUPPORTED_EXCHANGES:
    if exchange_name == Location.BINANCEUS:
        continue
    hiddenimports.append(f'rotkehlchen.exchanges.{exchange_name}')

# TODO: Make this dynamic you dummy
ethereum_modules = collect_submodules('rotkehlchen.chain.ethereum.modules')
optimism_modules = collect_submodules('rotkehlchen.chain.optimism.modules')
polygon_pos_modules = collect_submodules('rotkehlchen.chain.polygon_pos.modules')
arbitrum_one_modules = collect_submodules('rotkehlchen.chain.arbitrum_one.modules')
gnosis_modules = collect_submodules('rotkehlchen.chain.gnosis.modules')
base_modules = collect_submodules('rotkehlchen.chain.base.modules')
dynamic_modules = ethereum_modules + optimism_modules + polygon_pos_modules + arbitrum_one_modules + gnosis_modules + base_modules
hiddenimports.extend(dynamic_modules)

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
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name=executable_name,
        debug=False,
        strip=False,
        upx=False,
        console=True,
        target_arch=MACOS_BUILD_ARCH
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name='rotki-core',
    )
