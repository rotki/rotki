import os

from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = []
if os.name == 'nt':
    # I don't know why but in Windows the python executable does not seem
    # to properly copy libsecp256k1.dll
    # OSError: cannot load library 'C:\Users\lefteris\AppData\Local\Temp\_MEI50802\coincurve\libsecp256k1.dll': error 0x7e.  Additionally, ctypes.util.find_library()did not manage to locate a library called 'C:\\Users\\lefteris\\AppData\\Local\\Temp\\_MEI50802\\coincurve\\libsecp256k1.dll'  # noqa: E501
    # [4952] Failed to execute script rotkehlchen-script

    # With this the dll is bundled correctly
    binaries = collect_dynamic_libs('coincurve')
