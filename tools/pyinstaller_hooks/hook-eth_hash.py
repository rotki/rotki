from PyInstaller.utils.hooks import copy_metadata

hiddenimports = ['eth_hash.backends.pycryptodome']
datas = copy_metadata('eth_hash')
