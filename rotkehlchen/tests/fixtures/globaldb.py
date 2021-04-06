from pathlib import Path
from shutil import copyfile
from typing import List, Optional

import pytest

from rotkehlchen.chain.ethereum.typing import CustomEthereumToken
from rotkehlchen.globaldb import GlobalDBHandler


@pytest.fixture(name='custom_ethereum_tokens')
def fixture_custom_ethereum_tokens() -> Optional[List[CustomEthereumToken]]:
    return None


def create_globaldb(
        data_directory,
) -> GlobalDBHandler:
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    GlobalDBHandler._GlobalDBHandler__instance = None  # type: ignore

    handler = GlobalDBHandler(data_dir=data_directory)
    # note: the addition of custom ethereum tokens is moved after resolver initialization
    # so that DB can be primed with all assets.json
    return handler


@pytest.fixture(name='globaldb')
def fixture_globaldb(globaldb_version, tmpdir_factory):
    root_dir = Path(__file__).resolve().parent.parent.parent
    if globaldb_version is None:  # no specific version -- normal test
        source_db_path = root_dir / 'data' / 'global.db'
    else:
        source_db_path = root_dir / 'tests' / 'data' / f'v{globaldb_version}_global.db'
    new_data_dir = Path(tmpdir_factory.mktemp('test_data_dir'))
    new_global_dir = new_data_dir / 'global_data'
    new_global_dir.mkdir(parents=True, exist_ok=True)
    copyfile(source_db_path, new_global_dir / 'global.db')
    return create_globaldb(new_data_dir)


@pytest.fixture(name='globaldb_version')
def fixture_globaldb_version() -> Optional[int]:
    return None
