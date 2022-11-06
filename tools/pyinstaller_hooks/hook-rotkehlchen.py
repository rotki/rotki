import os

import pkg_resources

datas = []
# eth-hash, and eth-utils seem to have a cyclic dependency and they keep adding
# each other to the required_packages resulting in a while loop that never terminates.
# This set keeps track of the already processed packages to avoid re-adding them.
processed = set()


# This is only needed until https://github.com/pyinstaller/pyinstaller/issues/3033 is fixed
# Until then can't use PyInstaller.utils.hooks import copy_metadata
def copy_metadata(package_name):
    dist = pkg_resources.get_distribution(package_name)
    metadata_dir = dist.egg_info
    return [(metadata_dir, metadata_dir[len(dist.location) + len(os.sep):])]


# Add metadata of all required packages to allow pkg_resources.require() to work
required_packages = [("rotkehlchen", [])]
while required_packages:
    req_name, req_extras = required_packages.pop()
    for req in pkg_resources.get_distribution(req_name).requires(req_extras):
        if req.project_name in processed:
            continue
        required_packages.append((req.project_name, list(req.extras)))
    try:
        datas.extend(copy_metadata(req_name))
        processed.add(req_name)
    except AssertionError:
        pass
