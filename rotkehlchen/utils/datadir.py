import logging
from pathlib import Path
from shutil import Error, copytree, move, rmtree

from rotkehlchen.constants.misc import (
    ALLASSETIMAGESDIR_NAME,
    APPDIR_NAME,
    ASSETIMAGESDIR_NAME,
    AVATARIMAGESDIR_NAME,
    CUSTOMASSETIMAGESDIR_NAME,
    GLOBALDIR_NAME,
    IMAGESDIR_NAME,
    MISCDIR_NAME,
    USERDB_NAME,
    USERSDIR_NAME,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _create_directory_with_potential_backup(data_dir: Path, name: str) -> Path:
    """Create a subdirectory under the main data directory. If the directory
    already exists and has a user database in it, that means that someone made
    a user with that name. In which edge case we will try to rename and backup"""
    subdir = data_dir / name
    if (subdir / USERDB_NAME).exists():
        # someone had a user, called name ... and did not get moved with initial for loop
        try:  # this should not happen actually ...
            backup_name = f'auto_backup_{name}_user_{ts_now()}'
            copytree(subdir, backup_name)
            log.debug(f'Found old style user with name {name}. Backing it up at {backup_name}')
        except (PermissionError, Error) as e:
            log.error(f'During restructuring data directory failed to make a backup of a user called {name} due to {e}')  # noqa: E501
        else:
            rmtree(subdir, ignore_errors=True)

    subdir.mkdir(parents=True, exist_ok=True)
    return subdir


def _move_paths_to_directory(paths: list[Path], target_dir: Path) -> None:
    """Move given paths to the target directory"""
    for path in paths:
        target_path_dir = target_dir / path.name
        try:
            move(path, target_path_dir)
        except (PermissionError, Error) as e:
            log.error(f'During restructuring data directory failed to copy {path} to {target_path_dir} due to {e}')  # noqa: E501


def _handle_images(data_dir: Path, icons_path: Path | None) -> None:
    """Create the images data directory and move paths there"""
    if icons_path is not None:
        img_data_dir = _create_directory_with_potential_backup(data_dir, IMAGESDIR_NAME)
        assets_dir = img_data_dir / ASSETIMAGESDIR_NAME
        assets_dir.mkdir(parents=True, exist_ok=True)

        targetpath = assets_dir / ALLASSETIMAGESDIR_NAME
        try:
            move(icons_path, targetpath)
        except (PermissionError, Error) as e:
            log.error(f'During restructuring data directory failed to move {icons_path} to {targetpath} due to {e}')  # noqa: E501
            return

        all_assets_dir = targetpath
        for name, target_dir in ((AVATARIMAGESDIR_NAME, img_data_dir), (CUSTOMASSETIMAGESDIR_NAME, assets_dir)):  # noqa: E501
            subdir = all_assets_dir / name
            if not subdir.exists():
                continue

            targetpath = target_dir / name
            try:
                move(subdir, targetpath)
            except (PermissionError, Error) as e:
                log.error(f'During restructuring data directory failed to move {subdir} to {targetpath} due to {e}')  # noqa: E501


def maybe_restructure_rotki_data_directory(data_dir: Path) -> None:
    """Restructures the data directory to contain users under a specficic subdirectory
    and other kind of data under other ones. Essentially implement:
    https://github.com/rotki/rotki/issues/4841

    TODO: This should stay here for only a few versions and later be removed. This
    restructuring can always be done by the user in a super weird edge case, by hand.
    """
    if not (data_dir / 'global_data').is_dir():
        return  # probably already restructured

    user_paths = []
    other_paths = []
    global_path = airdrops_path = airdrops_poap_path = misc_path = icons_path = None
    for x in data_dir.iterdir():
        try:
            if not x.is_dir():
                other_paths.append(x)
                continue

            if (x / USERDB_NAME).exists():
                user_paths.append(x)
            elif x.name == 'global_data':
                global_path = x
            elif x.name == 'airdrops':
                airdrops_path = x
            elif x.name == 'airdrops_poap':
                airdrops_poap_path = x
            elif x.name == MISCDIR_NAME:
                misc_path = x
            elif x.name == 'icons':
                icons_path = x
            else:
                other_paths.append(x)

        except PermissionError:
            # ignore directories that can't be accessed
            continue

    # create the user_data directory and move users there
    user_data_dir = _create_directory_with_potential_backup(data_dir, USERSDIR_NAME)
    _move_paths_to_directory(user_paths, user_data_dir)

    # create the application data directory and move paths there
    app_data_dir = _create_directory_with_potential_backup(data_dir, APPDIR_NAME)
    _move_paths_to_directory([x for x in (airdrops_path, airdrops_poap_path, misc_path) if x is not None], app_data_dir)  # noqa: E501

    _handle_images(data_dir=data_dir, icons_path=icons_path)
    if global_path is not None:
        global_data_dir = _create_directory_with_potential_backup(data_dir, GLOBALDIR_NAME)
        rmtree(global_data_dir)
        try:
            move(global_path, global_data_dir)
        except (PermissionError, Error) as e:
            log.error(f'During restructuring data directory failed to copy {global_path} to {global_data_dir} due to {e}')  # noqa: E501

    # create the restructuring remnants directory and move all other paths there
    if len(other_paths) != 0:
        remnants_dir = _create_directory_with_potential_backup(data_dir, 'restructuring_remnants')
        _move_paths_to_directory(other_paths, remnants_dir)
