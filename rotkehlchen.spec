# -*- mode: python -*-
from __future__ import print_function  # isort:skip
import platform
import sys
from distutils.spawn import find_executable

from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.utils.misc import get_system_spec

"""
PyInstaller spec file to build single file or dir distributions

Currently only tested on macOS
"""

# Set to false to produce an exploded single-dir
ONEFILE = int(os.environ.get('ONEFILE', True))


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
        datas=datas
    )


# We don't need Tk and friends
sys.modules['FixTk'] = None

executable_name = 'rotkehlchen-{}-{}'.format(
    get_system_spec()['rotkehlchen'],
    'macos' if platform.system() == 'Darwin' else platform.system().lower())

hiddenimports = ['cytoolz.utils', 'cytoolz._signatures']
# Since the exchanges are loaded dynamically and some of them may not be detected
# by pyinstaller (https://github.com/rotki/rotki/issues/602) make sure they are
# all included as imports in the created executable
for exchange_name in SUPPORTED_EXCHANGES:
    hiddenimports.append(f'rotkehlchen.exchanges.{exchange_name}')

a = Entrypoint(
    'rotkehlchen',
    'console_scripts',
    'rotkehlchen',
    hookspath=['tools/pyinstaller_hooks'],
    hiddenimports=hiddenimports,
    datas=[
        ('rotkehlchen/data/eth_abi.json', 'rotkehlchen/data'),
        ('rotkehlchen/data/eth_contracts.json', 'rotkehlchen/data'),
        ('rotkehlchen/data/all_assets.json', 'rotkehlchen/data'),
        ('rotkehlchen/data/all_assets.meta', 'rotkehlchen/data'),
        ('rotkehlchen/data/uniswapv2_lp_tokens.json', 'rotkehlchen/data'),
        ('rotkehlchen/data/uniswapv2_lp_tokens.meta', 'rotkehlchen/data'),
        ('rotkehlchen/data/global.db', 'rotkehlchen/data'),
        ('rotkehlchen/data/curve_pools.json', 'rotkehlchen/data'),
    ],
    excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'packaging'],
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
        console=True
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
        console=True
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name='rotkehlchen'
    )
