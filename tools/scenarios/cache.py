"""Content-addressed local cache for built scenario profiles.

Key = (profile name, user DB schema version, hash of this package's sources +
the packaged global DB). A schema migration, generator change or packaged
asset-DB change naturally busts the cache. Mirrors the CI pattern used for
frontend/app/.e2e/data.

Consumers must always work on a COPY of a cached profile: booting the backend
mutates the user DB (settings writes, upgrade bookkeeping), so the cached
build itself must stay pristine.
"""
import hashlib
import shutil
from pathlib import Path
from typing import Final

from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION

CACHE_ROOT: Final = Path('~/.cache/rotki-scenarios').expanduser()
BUILD_MARKER: Final = 'BUILD_OK'

_PACKAGE_DIR: Final = Path(__file__).resolve().parent
_PACKAGED_GLOBALDB: Final = _PACKAGE_DIR.parents[1] / 'rotkehlchen' / 'data' / 'global.db'


def compute_cache_key(profile: str) -> str:
    hasher = hashlib.sha256()
    for path in sorted(_PACKAGE_DIR.rglob('*.py')):
        hasher.update(path.relative_to(_PACKAGE_DIR).as_posix().encode())
        hasher.update(path.read_bytes())
    hasher.update(_PACKAGED_GLOBALDB.read_bytes())
    return f'{profile}-v{ROTKEHLCHEN_DB_VERSION}-{hasher.hexdigest()[:12]}'


def cached_profile_path(key: str) -> Path | None:
    """Path of a completed cached build for the key, or None"""
    if ((path := CACHE_ROOT / key) / BUILD_MARKER).exists():
        return path
    return None


def new_build_dir(key: str) -> Path:
    """A fresh build directory on the same filesystem as the cache so the
    final move is atomic. Any stale leftover from an interrupted build is
    removed."""
    build_dir = CACHE_ROOT / f'{key}.building'
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    return build_dir


def commit_build(key: str, build_dir: Path) -> Path:
    """Mark a build complete and move it into its cache slot"""
    (build_dir / BUILD_MARKER).touch()
    if (target := CACHE_ROOT / key).exists():
        shutil.rmtree(target)
    build_dir.rename(target)
    return target


def materialize(cached_path: Path, output_dir: Path) -> None:
    """Copy a cached build to an output directory for actual use"""
    if output_dir.exists():
        raise FileExistsError(f'output directory {output_dir} already exists')
    shutil.copytree(cached_path, output_dir)
    (output_dir / BUILD_MARKER).unlink()
