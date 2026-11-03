from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

from flask import Response, send_file

from rotkehlchen.api.rest_helpers.downloads import register_post_download_cleanup
from rotkehlchen.api.result import ApiResult, FailResult, OkResult
from rotkehlchen.constants.limits import FREE_USER_NOTES_LIMIT
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.snapshots import DBSnapshot
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import InputError, RemoteError, TagConstraintError
from rotkehlchen.utils.snapshots import parse_import_snapshot_data

if TYPE_CHECKING:
    from rotkehlchen.db.filtering import AddressbookFilterQuery, UserNotesFilterQuery
    from rotkehlchen.db.utils import DBAssetBalance, LocationData
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.types import (
        AddressbookEntry,
        AddressbookType,
        ChecksumEvmAddress,
        HexColorCode,
        ModuleName,
        OptionalChainAddress,
        Timestamp,
        UserNote,
    )

from rotkehlchen.chain.evm.names import (
    find_ens_mappings,
    maybe_resolve_name,
    search_for_addresses_names,
)


class UserDataService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def get_tags(self) -> ApiResult:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            result = self.rotkehlchen.data.db.get_tags(cursor)
            response = {name: data.serialize() for name, data in result.items()}
        return OkResult(response)

    def add_tag(
            self,
            name: str,
            description: str | None,
            background_color: HexColorCode,
            foreground_color: HexColorCode,
    ) -> ApiResult:
        with self.rotkehlchen.data.db.user_write() as cursor:
            try:
                self.rotkehlchen.data.db.add_tag(
                    write_cursor=cursor,
                    name=name,
                    description=description,
                    background_color=background_color,
                    foreground_color=foreground_color,
                )
            except TagConstraintError as e:
                return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.CONFLICT)

            result = self.rotkehlchen.data.db.get_tags(cursor)
            response = {tag_name: data.serialize() for tag_name, data in result.items()}
        return OkResult(response)

    def edit_tag(
            self,
            name: str,
            new_name: str | None,
            description: str | None,
            background_color: HexColorCode | None,
            foreground_color: HexColorCode | None,
    ) -> ApiResult:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.edit_tag(
                    write_cursor=cursor,
                    name=name,
                    new_name=new_name,
                    description=description,
                    background_color=background_color,
                    foreground_color=foreground_color,
                )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)
        except TagConstraintError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.CONFLICT)

        return self.get_tags()

    def delete_tag(self, name: str) -> ApiResult:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.delete_tag(cursor, name=name)
        except TagConstraintError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return self.get_tags()

    def add_ignored_action_ids(self, action_ids: list[str]) -> ApiResult:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.add_to_ignored_action_ids(
                    write_cursor=cursor,
                    identifiers=action_ids,
                )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)

        return OkResult(True)

    def remove_ignored_action_ids(self, action_ids: list[str]) -> ApiResult:
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                self.rotkehlchen.data.db.remove_from_ignored_action_ids(
                    write_cursor=cursor,
                    identifiers=action_ids,
                )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)

        return OkResult(True)

    def get_user_notes(self, filter_query: UserNotesFilterQuery) -> ApiResult:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            user_notes, entries_found = self.rotkehlchen.data.db.get_user_notes_and_limit_info(
                filter_query=filter_query,
                cursor=cursor,
                has_premium=self.rotkehlchen.premium is not None,
            )
            user_notes_total = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='user_notes',
            )
        entries = [entry.serialize() for entry in user_notes]
        result = {
            'entries': entries,
            'entries_found': entries_found,
            'entries_total': user_notes_total,
            'entries_limit': FREE_USER_NOTES_LIMIT if self.rotkehlchen.premium is None else -1,
        }
        return OkResult(result)

    def add_user_note(
            self,
            title: str,
            content: str,
            location: str,
            is_pinned: bool,
    ) -> ApiResult:
        try:
            note_id = self.rotkehlchen.data.db.add_user_note(
                title=title,
                content=content,
                location=location,
                is_pinned=is_pinned,
                has_premium=self.rotkehlchen.premium is not None,
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(note_id)

    def edit_user_note(self, user_note: UserNote) -> ApiResult:
        try:
            self.rotkehlchen.data.db.edit_user_note(user_note=user_note)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(True)

    def delete_user_note(self, identifier: int) -> ApiResult:
        try:
            self.rotkehlchen.data.db.delete_user_note(identifier=identifier)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(True)

    def get_addressbook_entries(
            self,
            book_type: AddressbookType,
            filter_query: AddressbookFilterQuery,
    ) -> ApiResult:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        with db_addressbook.read_ctx(book_type) as cursor:
            entries, entries_found = db_addressbook.get_addressbook_entries(
                cursor=cursor,
                filter_query=filter_query,
            )
            entries_total = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='address_book',
            )
        serialized = [entry.serialize() for entry in entries]
        result = {
            'entries': serialized,
            'entries_found': entries_found,
            'entries_total': entries_total,
        }
        return OkResult(result)

    def add_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
            update_existing: bool,
    ) -> ApiResult:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        try:
            with db_addressbook.write_ctx(book_type) as write_cursor:
                db_addressbook.add_or_update_addressbook_entries(
                    write_cursor=write_cursor,
                    entries=entries,
                    update_existing=update_existing,
                )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(True)

    def update_addressbook_entries(
            self,
            book_type: AddressbookType,
            entries: list[AddressbookEntry],
    ) -> ApiResult:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        try:
            db_addressbook.update_addressbook_entries(book_type=book_type, entries=entries)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(True)

    def delete_addressbook_entries(
            self,
            book_type: AddressbookType,
            chain_addresses: list[OptionalChainAddress],
    ) -> ApiResult:
        db_addressbook = DBAddressbook(self.rotkehlchen.data.db)
        try:
            db_addressbook.delete_addressbook_entries(
                book_type=book_type,
                chain_addresses=chain_addresses,
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(True)

    def search_for_names_everywhere(
            self,
            chain_addresses: list[OptionalChainAddress],
    ) -> ApiResult:
        mappings = search_for_addresses_names(
            prioritizer=self.rotkehlchen.addressbook_prioritizer,
            chain_addresses=chain_addresses,
        )
        return OkResult(mappings)

    def get_queried_addresses_per_module(self) -> ApiResult:
        result = QueriedAddresses(self.rotkehlchen.data.db).get_queried_addresses_per_module()
        return OkResult(result)

    def add_queried_address_per_module(
            self,
            module: ModuleName,
            address: ChecksumEvmAddress,
    ) -> ApiResult:
        try:
            QueriedAddresses(self.rotkehlchen.data.db).add_queried_address_for_module(
                module,
                address,
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return self.get_queried_addresses_per_module()

    def remove_queried_address_per_module(
            self,
            module: ModuleName,
            address: ChecksumEvmAddress,
    ) -> ApiResult:
        try:
            QueriedAddresses(self.rotkehlchen.data.db).remove_queried_address_for_module(
                module,
                address,
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return self.get_queried_addresses_per_module()

    def get_ens_mappings(
            self,
            addresses: list[ChecksumEvmAddress],
            ignore_cache: bool,
    ) -> ApiResult:
        try:
            mappings = find_ens_mappings(
                ethereum_inquirer=self.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
                addresses=addresses,
                ignore_cache=ignore_cache,
            )
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, e.cause)
        return OkResult(mappings)

    def resolve_ens_name(self, name: str, ignore_cache: bool) -> ApiResult:
        try:
            address = maybe_resolve_name(
                ethereum_inquirer=self.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
                name=name,
                ignore_cache=ignore_cache,
            )
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.NOT_FOUND, e.cause)
        if address is None:
            return FailResult('', HTTPStatus.NOT_FOUND, FailureCause.NOT_FOUND)
        return OkResult(address)

    def get_user_db_snapshot(self, timestamp: Timestamp) -> ApiResult:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            balances = dbsnapshot.get_timed_balances(cursor, timestamp=timestamp)
            location_data = dbsnapshot.get_timed_location_data(cursor, timestamp=timestamp)
        if len(balances) == 0 or len(location_data) == 0:
            return FailResult(
                'No snapshot data found for the given timestamp.',
                HTTPStatus.NOT_FOUND,
                FailureCause.NOT_FOUND,
            )

        serialized_balances = [entry.serialize() for entry in balances]
        serialized_location_data = [entry.serialize() for entry in location_data]
        result = {
            'balances_snapshot': serialized_balances,
            'location_data_snapshot': serialized_location_data,
        }
        return OkResult(result)

    def edit_user_db_snapshot(
            self,
            timestamp: Timestamp,
            location_data_snapshot: list[LocationData],
            balances_snapshot: list[DBAssetBalance],
    ) -> ApiResult:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                dbsnapshot.update(
                    write_cursor=cursor,
                    timestamp=timestamp,
                    balances_snapshot=balances_snapshot,
                    location_data_snapshot=location_data_snapshot,
                )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(True)

    def export_user_db_snapshot(self, timestamp: Timestamp, path: Path) -> ApiResult:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        is_success, message = dbsnapshot.export(timestamp=timestamp, directory_path=path)
        if is_success is False:
            return FailResult(message, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return OkResult(True)

    def download_user_db_snapshot(self, timestamp: Timestamp) -> ApiResult | Response:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        is_success, zipfile_path = dbsnapshot.export(timestamp, directory_path=None)
        if is_success is False:
            return FailResult(
                'Could not create a zip archive',
                HTTPStatus.CONFLICT,
                FailureCause.LOCAL_DB,
            )

        try:
            download_response = send_file(
                path_or_file=zipfile_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name='snapshot.zip',
            )
            return register_post_download_cleanup(download_response, Path(zipfile_path))
        except FileNotFoundError:
            return FailResult('No file was found', HTTPStatus.NOT_FOUND, FailureCause.NOT_FOUND)

    def delete_user_db_snapshot(self, timestamp: Timestamp) -> ApiResult:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                dbsnapshot.delete(
                    write_cursor=write_cursor,
                    timestamp=timestamp,
                )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(True)

    def import_user_snapshot(
            self,
            balances_snapshot_file: Path,
            location_data_snapshot_file: Path,
    ) -> ApiResult:
        dbsnapshot = DBSnapshot(
            db_handler=self.rotkehlchen.data.db,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        )
        error_or_empty, processed_balances, processed_location_data = parse_import_snapshot_data(
            balances_snapshot_file=balances_snapshot_file,
            location_data_snapshot_file=location_data_snapshot_file,
        )
        if error_or_empty != '':
            return FailResult(error_or_empty, HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                dbsnapshot.import_snapshot(
                    write_cursor=write_cursor,
                    processed_balances_list=processed_balances,
                    processed_location_data_list=processed_location_data,
                )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(True)
