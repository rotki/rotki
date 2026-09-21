from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from rotkehlchen.db.locations import DBLocations
from rotkehlchen.errors.misc import InputError
from rotkehlchen.icons import check_if_image_is_cached, maybe_create_image_response
from rotkehlchen.locations.images import (
    delete_location_image,
    location_images_dir,
    store_location_image,
)

if TYPE_CHECKING:
    from pathlib import Path
    from types import EllipsisType

    from flask import Response

    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.locations.types import LocationIdentifier, LocationNode
    from rotkehlchen.rotkehlchen import Rotkehlchen


def _error(message: str, status_code: HTTPStatus) -> dict[str, Any]:
    return {'result': None, 'message': message, 'status_code': status_code}


def _ok(result: Any) -> dict[str, Any]:
    return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}


def _not_found(identifier: str) -> dict[str, Any]:
    return _error(f'Location {identifier} does not exist', HTTPStatus.NOT_FOUND)


class LocationsService:
    """Request level handling of the location tree. The tree rules live in DBLocations."""

    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen
        self.db_locations = DBLocations()

    @property
    def _images_dir(self) -> Path:
        assert self.rotkehlchen.data.user_data_dir is not None, 'only called when logged in'
        return location_images_dir(self.rotkehlchen.data.user_data_dir)

    def get_locations(self) -> dict[str, Any]:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            return _ok([x.serialize() for x in self.db_locations.get_all(cursor)])

    def add_location(
            self,
            name: str,
            parent_identifier: LocationIdentifier,
            icon: str | None,
    ) -> dict[str, Any]:
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                node = self.db_locations.add_custom(
                    write_cursor=write_cursor,
                    name=name,
                    parent_identifier=parent_identifier,
                    icon=icon,
                )
        except InputError as e:
            return _error(str(e), HTTPStatus.BAD_REQUEST)

        return _ok(node.serialize())

    def _path_names(self, cursor: DBCursor, node: LocationNode) -> list[str]:
        if node.parent_identifier is None:
            return [node.name]
        return [*self.db_locations.path_names(cursor, node.parent_identifier), node.name]

    def edit_location(
            self,
            identifier: LocationIdentifier,
            name: str | None,
            parent_identifier: LocationIdentifier | None,
            icon: str | EllipsisType | None,
            is_active: bool | None,
            dry_run: bool,
    ) -> dict[str, Any]:
        """Edit a custom location, or with dry_run only check the edit. The display path
        before and after the edit lets the client warn that a move changes where the
        location's history is aggregated."""
        db = self.rotkehlchen.data.db
        with db.conn.read_ctx() as cursor:
            if (old_node := self.db_locations.get(cursor, identifier)) is None:
                return _not_found(identifier)
            old_path = self._path_names(cursor, old_node)

        try:
            with db.conn.read_ctx() if dry_run else db.user_write() as cursor:
                node = self.db_locations.edit_custom(
                    write_cursor=cursor,
                    identifier=identifier,
                    name=name,
                    parent_identifier=parent_identifier,
                    icon=icon,
                    is_active=is_active,
                    dry_run=dry_run,
                )
                new_path = self._path_names(cursor, node)
        except InputError as e:
            return _error(str(e), HTTPStatus.BAD_REQUEST)

        return _ok({'location': node.serialize(), 'old_path': old_path, 'new_path': new_path})

    def delete_location(self, identifier: LocationIdentifier) -> dict[str, Any]:
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                if self.db_locations.get(write_cursor, identifier) is None:
                    return _not_found(identifier)
                node = self.db_locations.delete_custom(write_cursor, identifier)
        except InputError as e:
            return _error(str(e), HTTPStatus.CONFLICT)

        delete_location_image(self._images_dir, node.image)
        return _ok(True)

    def get_location_aliases(self) -> dict[str, Any]:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            aliases = self.db_locations.get_aliases(cursor)
        return _ok([
            {'alias': alias, 'location_identifier': identifier}
            for alias, identifier in aliases.items()
        ])

    def set_location_alias(self, alias: str, identifier: LocationIdentifier) -> dict[str, Any]:
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                self.db_locations.set_alias(write_cursor, alias, identifier)
        except InputError as e:
            return _error(str(e), HTTPStatus.BAD_REQUEST)
        return _ok(True)

    def delete_location_alias(self, alias: str) -> dict[str, Any]:
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                self.db_locations.delete_alias(write_cursor, alias)
        except InputError as e:
            return _error(str(e), HTTPStatus.NOT_FOUND)
        return _ok(True)

    def get_location_usage(self, identifier: LocationIdentifier) -> dict[str, Any]:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if (node := self.db_locations.get(cursor, identifier)) is None:
                return _not_found(identifier)
            usage = self.db_locations.usage(cursor, identifier)

        return _ok({
            'usage': usage,
            'deletable': not node.is_builtin and len(usage) == 0,
        })

    def upload_location_image(
            self,
            identifier: LocationIdentifier,
            filepath: Path,
    ) -> dict[str, Any]:
        """Store the image, then point the location at it and remove the image it replaces,
        so a failure never leaves the location without a readable image"""
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if self.db_locations.get(cursor, identifier) is None:
                return _not_found(identifier)

        try:
            image = store_location_image(self._images_dir, identifier, filepath)
        except OSError as e:
            return _error(f'Failed to store the location image: {e!s}', HTTPStatus.CONFLICT)

        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                old_image = self.db_locations.set_custom_image(write_cursor, identifier, image)
        except InputError as e:
            delete_location_image(self._images_dir, image)
            return _error(str(e), HTTPStatus.BAD_REQUEST)

        if old_image != image:
            delete_location_image(self._images_dir, old_image)
        return _ok({'image': image})

    def delete_location_image(self, identifier: LocationIdentifier) -> dict[str, Any]:
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                if self.db_locations.get(write_cursor, identifier) is None:
                    return _not_found(identifier)
                old_image = self.db_locations.set_custom_image(write_cursor, identifier, None)
        except InputError as e:
            return _error(str(e), HTTPStatus.BAD_REQUEST)

        delete_location_image(self._images_dir, old_image)
        return _ok(True)

    def get_location_image(self, identifier: LocationIdentifier, match_header: str | None) -> Response:  # noqa: E501
        """The uploaded image of a custom location. Images of built-in locations are packaged
        with the frontend, so they are never served here."""
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            node = self.db_locations.get(cursor, identifier)

        if node is None or node.is_builtin or node.image is None:
            return maybe_create_image_response(None)

        image_path = self._images_dir / node.image
        if image_path.is_file() and (cached := check_if_image_is_cached(image_path, match_header)) is not None:  # noqa: E501
            return cached
        return maybe_create_image_response(image_path)
