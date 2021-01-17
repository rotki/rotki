from PyInstaller.utils.hooks import collect_data_files

# scalecodec has a lot of json files from which it loads the types
# we need to make sure pyinstaller bundles them in the created binary
datas = collect_data_files('scalecodec')
