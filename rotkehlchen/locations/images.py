"""Images uploaded for custom locations.

They live in the user's data directory, next to the user DB, since custom locations belong to
that user. A file is named by the immutable location identifier and a digest of its content,
so replacing an image gives it a new name and clients may cache every name indefinitely.
"""
import shutil
import urllib.parse
from typing import TYPE_CHECKING, Final

from rotkehlchen.constants.misc import IMAGESDIR_NAME
from rotkehlchen.utils.hashing import file_md5

if TYPE_CHECKING:
    from pathlib import Path

LOCATION_IMAGES_DIRNAME: Final = 'locations'


def location_images_dir(user_data_dir: Path) -> Path:
    return user_data_dir / IMAGESDIR_NAME / LOCATION_IMAGES_DIRNAME


def store_location_image(images_dir: Path, identifier: str, upload: Path) -> str:
    """Copy an uploaded image for the location and return the stored file name.

    The upload's extension must already be validated. May raise OSError.
    """
    images_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        f'{urllib.parse.quote_plus(identifier)}_{file_md5(upload)[:16]}{upload.suffix.lower()}'
    )
    shutil.copyfile(upload, images_dir / filename)
    return filename


def delete_location_image(images_dir: Path, filename: str | None) -> None:
    if filename is not None:
        (images_dir / filename).unlink(missing_ok=True)
