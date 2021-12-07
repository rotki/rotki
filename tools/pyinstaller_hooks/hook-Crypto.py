import glob
import os

from PyInstaller.compat import EXTENSION_SUFFIXES
from PyInstaller.utils.hooks import get_module_file_attribute

"""
Add Cryptodome (imports as Crypto) binary modules
"""

binaries = []
binary_module_names = [
    'Crypto.Cipher',
    'Crypto.Util',
    'Crypto.Hash',
    'Crypto.Protocol',
]

for module_name in binary_module_names:
    module_dir = os.path.dirname(get_module_file_attribute(module_name))
    for ext in EXTENSION_SUFFIXES:
        module_bin = glob.glob(os.path.join(module_dir, '_*{}'.format(ext)))
        for filename in module_bin:
            binaries.append((filename, module_name.replace('.', '/')))
