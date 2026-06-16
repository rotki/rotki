# -*- mode: python -*-
from __future__ import print_function  # isort:skip
import os
import platform
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

from rotkehlchen.constants.misc import GLOBALDB_NAME
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.types import CHAINS_WITH_TRANSACTION_DECODERS, Location
from rotkehlchen.utils.misc import get_system_spec

"""
PyInstaller spec file to build one-folder distributions.
"""

MACOS_IDENTITY = os.environ.get('IDENTITY', None)
# Strip debug symbols from bundled native libraries unless an opt-in test build
# of the backend with debug symbols was requested (see package.py). Skipped on
# Windows because PyInstaller drives GNU `strip` (available on the CI via
# Strawberry Perl/MSYS), which corrupts PE binaries like python311.dll and
# causes the resulting bundle to fail with "LoadLibrary: Invalid access to
# memory location." Windows debug info lives in separate PDB files anyway, so
# there is nothing to gain from stripping the bundled .dll/.pyd files.
STRIP_BINARIES = (
    platform.system().lower() != 'windows'
    and os.environ.get('ROTKI_BACKEND_DEBUG_SYMBOLS', '').lower() not in {'1', 'true', 'yes', 'on'}
)


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

for chain in CHAINS_WITH_TRANSACTION_DECODERS:  # load modules from the chains that have decoders
    hiddenimports.extend(collect_submodules(f'rotkehlchen.chain.{chain.name.lower()}.modules'))

hiddenimports.extend(collect_submodules('rotkehlchen.mcp.tools'))

a = Entrypoint(
    'rotkehlchen',
    'console_scripts',
    'rotkehlchen',
    hookspath=['tools/pyinstaller_hooks'],
    hiddenimports=hiddenimports,
    datas=[
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
        ('rotkehlchen/data/solana_tokens_data.csv', 'rotkehlchen/data'),
        # TODO
        # We probably should have a better way to specify some data should be loaded
        # by a module in pyinstaller. Should be loaded dynamically by rotki and not
        # by pyinstaller if we want it to be truly modular
        (
            'rotkehlchen/chain/ethereum/modules/dxdaomesa/data/contracts.json',
            'rotkehlchen/chain/ethereum/modules/dxdaomesa/data',
        ),
    ],
    excludes=[
        'FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'debugimporter',
        # polars submodules we never import. polars.sql is NOT excluded because
        # polars/__init__.py unconditionally imports SQLContext from it.
        'polars.testing', 'polars.ml',
        # SelfTest suites bundled inside pycryptodome and pycryptodomex.
        'Crypto.SelfTest', 'Cryptodome.SelfTest',
        # Test packages shipped inside runtime dependencies. None of these are
        # imported at runtime; gevent.testing is only used by gevent.tests
        # and a towncrier release helper in gevent/_util.py.
        'gevent.tests', 'gevent.testing',
        'greenlet.tests',
        'zope.interface.tests',
        'regex.tests',
        'cytoolz.tests', 'toolz.tests',
        'parsimonious.tests',
        # substrate-interface ships smoldot_light (~24 MB) as an optional
        # transport, loaded lazily inside a try/except. rotki only uses the
        # RPC/WebSocket transport, so the binding is never instantiated.
        'smoldot_light',
    ],
)

# Drop unused Google API discovery descriptors. google-api-python-client ships
# pre-built JSON descriptors for ~575 Google APIs (~93 MB total); we only build
# the Calendar v3 client (see rotkehlchen/externalapis/google_calendar.py).
def _keep_google_discovery_entry(dest):
    norm = dest.replace(os.sep, '/')
    if '/discovery_cache/documents/' not in norm:
        return True
    return norm.rsplit('/', 1)[-1].startswith('calendar')

a.datas = [entry for entry in a.datas if _keep_google_discovery_entry(entry[0])]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

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
    strip=STRIP_BINARIES,
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
    strip=STRIP_BINARIES,
    upx=False,
    name='rotki-core',
    codesign_identity=identity,
    entitlements_file=entitlements,
)
