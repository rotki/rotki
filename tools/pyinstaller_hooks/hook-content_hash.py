from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('content_hash')
