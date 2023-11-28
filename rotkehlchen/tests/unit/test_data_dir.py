import pytest

from rotkehlchen.constants.misc import (
    AVATARIMAGESDIR_NAME,
    CUSTOMASSETIMAGESDIR_NAME,
    GLOBALDB_NAME,
    MISCDIR_NAME,
    USERDB_NAME,
)
from rotkehlchen.utils.datadir import maybe_restructure_rotki_data_directory

USERS = ['lefteris', 'kelsos', 'luki']
BAD_USERS = ['app', 'global']
MISC_FILE = 'geoip-1234.mmdb'
ASSET_ICONS = ('ETH_small.png', 'KSM_small.png')
AIRDROPS = ('coswap.csv', 'lido.csv')
AVATARS = ('lefteris.eth.png', 'lito.eth.png')
CUSTOM_ICONS = ('f69e047e-cb4a-48a8-8382-8c78269866d5.png', 'cb4a-48a8-8382-8c78269844d5.png')
REMNANT_FILES = ('file1.txt', 'file2.json')
REMNANT_DIRS = ('random_dir1', 'random_dir2')


def _create_old_directory_structure(data_dir):
    """Create the old directory tree structure to test against it"""
    global_data = data_dir / 'global_data'
    global_data.mkdir(parents=True, exist_ok=True)
    (global_data / GLOBALDB_NAME).touch()

    for user in USERS:
        user_dir = data_dir / user
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / USERDB_NAME).touch()

    misc_data = data_dir / MISCDIR_NAME
    misc_data.mkdir(parents=True, exist_ok=True)
    (misc_data / MISC_FILE).touch()

    for name in ('airdrops', 'airdrops_poap'):
        subdir = data_dir / name
        subdir.mkdir(parents=True, exist_ok=True)
        for filename in AIRDROPS:
            (subdir / filename).touch()

    icons_data = data_dir / 'icons'
    icons_data.mkdir(parents=True, exist_ok=True)
    for name in ASSET_ICONS:
        (icons_data / name).touch()

    avatars_data = icons_data / AVATARIMAGESDIR_NAME
    avatars_data.mkdir(parents=True, exist_ok=True)
    for name in AVATARS:
        (avatars_data / name).touch()

    custom_data = icons_data / CUSTOMASSETIMAGESDIR_NAME
    custom_data.mkdir(parents=True, exist_ok=True)
    for name in CUSTOM_ICONS:
        (custom_data / name).touch()

    # also add two bad edge cases of username same as the new root directories we want to have
    for bad_user in BAD_USERS:
        user_dir = data_dir / bad_user
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / USERDB_NAME).touch()

    # add some random files / dirs to see they are not lost
    for random_file in REMNANT_FILES:
        (data_dir / random_file).touch()
    for random_dir in REMNANT_DIRS:
        (data_dir / random_dir).mkdir()


def _assert_dir_matches(directory, expected):
    contents = set()
    for x in directory.iterdir():
        contents.add(x.name)

    assert contents == set(expected)


def _assert_directory_structure(data_dir):
    """Asserts that the directory structure has been properly migrated"""
    for x in data_dir.iterdir():
        assert x.is_dir() and x.name in ('users', 'app', 'global', 'images', 'restructuring_remnants')  # noqa: E501

    # assert the proper directory structure for users
    users_dir = data_dir / 'users'
    users = set()
    for x in users_dir.iterdir():
        assert x.is_dir() and (x / USERDB_NAME).exists()
        users.add(x.name)
    assert users == set(USERS + BAD_USERS)

    # assert the proper directory structure for global data
    global_dir = data_dir / 'global'
    assert global_dir.is_dir()
    assert (global_dir / GLOBALDB_NAME).exists()

    # assert the proper directory structure for app data
    app_dir = data_dir / 'app'
    users = set()
    for x in app_dir.iterdir():
        if x.name in ('airdrops', 'airdrops_poap'):
            _assert_dir_matches(x, AIRDROPS)
        elif x.name == MISCDIR_NAME:
            assert (x / MISC_FILE).exists()
        else:
            raise AssertionError(f'Found unexpected path {x}')

    # assert the proper directory structure for images
    images_dir = data_dir / 'images'
    for x in images_dir.iterdir():
        if x.name == AVATARIMAGESDIR_NAME:
            _assert_dir_matches(x, AVATARS)
        elif x.name == 'assets':
            for y in x.iterdir():
                if y.name == 'all':
                    _assert_dir_matches(y, ASSET_ICONS)
                elif y.name == CUSTOMASSETIMAGESDIR_NAME:
                    _assert_dir_matches(y, CUSTOM_ICONS)
                else:
                    raise AssertionError(f'Found unexpected path {y}')
        else:
            raise AssertionError(f'Found unexpected path {x}')

    # assert remnants
    remnants_dir = data_dir / 'restructuring_remnants'
    for x in remnants_dir.iterdir():
        if x.name in REMNANT_FILES:
            assert x.exists()
        elif x.name in REMNANT_DIRS:
            assert x.is_dir()
        else:
            raise AssertionError(f'Found unexpected path {x}')


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_restructure_rotki_data_directory(data_dir):
    """Test that restructuring the rotki data directory works as expected"""
    _create_old_directory_structure(data_dir)
    maybe_restructure_rotki_data_directory(data_dir)
    _assert_directory_structure(data_dir)

    # make sure that running again does not mess things up
    maybe_restructure_rotki_data_directory(data_dir)
    _assert_directory_structure(data_dir)
