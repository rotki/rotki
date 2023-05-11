# Taken from:
# https://github.com/pyinstaller/pyinstaller/blob/9dd34bdfbaeaa4e0459bd3051d1caf0c7d75073f/PyInstaller/hooks/pre_find_module_path/hook-distutils.py
# This is a fix introduced in pyinstaller PR: https://github.com/pyinstaller/pyinstaller/pull/4372
# for https://github.com/pyinstaller/pyinstaller/issues/4064 that
# has not yet been included in a release.
# Once it is included in a release this hook can be removed

# -----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

"""
`distutils`-specific pre-find module path hook.

When run from within a venv (virtual environment), this hook changes the
`__path__` of the `distutils` package to that of the system-wide rather than
venv-specific `distutils` package. While the former is suitable for freezing,
the latter is intended for use _only_ from within venvs.
"""


import distutils
import os

from PyInstaller.utils.hooks import logger


def pre_find_module_path(api):
    # Absolute path of the system-wide "distutils" package when run from within
    # a venv or None otherwise.

    # opcode is not a virtualenv module, so we can use it to find the stdlib.
    # Technique taken from virtualenv's "distutils" package detection at
    # https://github.com/pypa/virtualenv/blob/16.3.0/virtualenv_embedded/distutils-init.py#L5
    import opcode

    system_module_path = os.path.normpath(os.path.dirname(opcode.__file__))
    loaded_module_path = os.path.normpath(os.path.dirname(distutils.__file__))
    if system_module_path != loaded_module_path:
        # Find this package in its parent directory.
        api.search_dirs = [system_module_path]
        logger.info('distutils: retargeting to non-venv dir %r',
                    system_module_path)
