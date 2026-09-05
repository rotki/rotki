import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v53->v54 upgrade')
def upgrade_v53_to_v54(db: DBHandler, progress_handler: DBUpgradeProgressHandler) -> None:
    """Upgrades the DB from v53 to v54. This happened in 1.45."""

    @progress_step(description='Add Sonic location.')
    def _add_sonic_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
            (Location.SONIC.serialize_for_db(), Location.SONIC.value),
        )

    @progress_step(description='Add Robinhood chain location.')
    def _add_robinhood_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
            (Location.ROBINHOOD.serialize_for_db(), Location.ROBINHOOD.value),
        )

    @progress_step(description='Add Ink chain location.')
    def _add_ink_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
            (Location.INK.serialize_for_db(), Location.INK.value),
        )

    @progress_step(description='Remove notes that rotki now generates from event data.')
    def _remove_generated_notes(write_cursor: DBCursor) -> None:
        """Notes of gas, approvals, deploys, transactions to self, plain transfers, ETH staking
        events and Solana fees are since this version generated at read time from the event's
        other columns. Null every stored note that still equals the text rotki generated for it,
        matching the templates of the decoders of this version. Notes edited by the user or
        extended by a protocol decoder no longer match the shape and stay.

        The asset symbol is not available in the user DB, so the patterns hold a GLOB wildcard
        in its place. GLOB is case sensitive, unlike LIKE, so a note only differing in case from
        the generated one (which can only be a user edit) is kept.
        """
        write_cursor.execute(  # staking event notes were never read back from the DB
            'UPDATE history_events SET notes=NULL WHERE entry_type IN (3, 4, 5)',  # withdrawal, block, deposit  # noqa: E501
        )
        evm_basics = 'H.entry_type=2 AND ('  # evm event
        write_cursor.execute(
            'UPDATE history_events SET notes=NULL WHERE identifier IN (SELECT H.identifier '
            'FROM history_events H JOIN chain_events_info C ON C.identifier=H.identifier WHERE '
            f"{evm_basics}"
            "(H.subtype='fee' AND C.counterparty='gas' AND ("
            "(H.type='spend' AND H.notes GLOB 'Burn ' || H.amount || ' * for gas') OR "
            "(H.type='fail' AND H.notes GLOB 'Burn ' || H.amount || ' * for gas of a failed transaction')"  # noqa: E501
            ')) OR '
            "(H.type='informational' AND H.subtype='approve' AND C.counterparty IS NULL AND ("
            "(H.amount='0' AND H.notes GLOB 'Revoke * spending approval of ' || H.location_label || ' by ' || C.address) OR "  # noqa: E501
            "(H.amount!='0' AND H.notes GLOB 'Set * spending approval of ' || H.location_label || ' by ' || C.address || ' to ' || H.amount)"  # noqa: E501
            ')) OR '
            "(H.type='deploy' AND H.notes='Deploy a new contract at ' || C.address) OR "
            "(H.type='transaction to self' AND H.subtype='none' AND ("
            "(H.amount='0' AND H.notes='No value transaction to self') OR "
            "(H.amount!='0' AND H.notes GLOB 'Transaction to self of ' || H.amount || ' *')"
            '))'
            '))',
        )
        # Plain transfers. The verb and preposition follow the type. Native asset transfers
        # name only the other side, token transfers both. The location codes and native asset
        # identifiers are those of the EVM chains with transactions at this version.
        verb = "CASE H.type WHEN 'spend' THEN 'Send' WHEN 'receive' THEN 'Receive' WHEN 'transfer' THEN 'Transfer' WHEN 'deposit' THEN 'Deposit' ELSE 'Withdraw' END"  # noqa: E501
        outgoing = "H.type IN ('spend', 'transfer', 'deposit')"
        other_side = 'COALESCE(C.counterparty, C.address)'
        native_asset = (
            "((H.location IN ('f', 'g', 'i', 'j', 'n', 'o', char(127)) AND H.asset='ETH') OR "  # ethereum, optimism, arbitrum, base, scroll, zksync lite, robinhood  # noqa: E501
            "(H.location='h' AND H.asset='eip155:137/erc20:0x0000000000000000000000000000000000001010') OR "  # polygon  # noqa: E501
            "(H.location='k' AND H.asset='XDAI') OR (H.location='v' AND H.asset='BNB') OR "  # gnosis, bsc  # noqa: E501
            "(H.location='y' AND H.asset='HYPE') OR (H.location='z' AND H.asset='MON') OR "  # hyperliquid, monad  # noqa: E501
            "(H.location='~' AND H.asset='S'))"  # sonic
        )
        write_cursor.execute(
            'UPDATE history_events SET notes=NULL WHERE identifier IN (SELECT H.identifier '
            'FROM history_events H JOIN chain_events_info C ON C.identifier=H.identifier WHERE '
            f"{evm_basics}"
            "((H.type IN ('spend', 'receive', 'transfer') AND H.subtype='none' AND C.counterparty IS NULL) OR "  # noqa: E501
            "(H.type='deposit' AND H.subtype='deposit asset' AND C.counterparty IS NOT NULL) OR "
            "(H.type='withdrawal' AND H.subtype='remove asset' AND C.counterparty IS NOT NULL)"
            ') AND ('
            f"({native_asset} AND H.notes GLOB {verb} || ' ' || H.amount || ' * ' || CASE WHEN {outgoing} THEN 'to' ELSE 'from' END || ' ' || {other_side}) OR "  # noqa: E501
            f"(NOT {native_asset} AND H.asset NOT LIKE '%/erc721:%' AND ("
            f"({outgoing} AND H.notes GLOB {verb} || ' ' || H.amount || ' * from ' || H.location_label || ' to ' || {other_side}) OR "  # noqa: E501
            f"(NOT {outgoing} AND H.notes GLOB {verb} || ' ' || H.amount || ' * from ' || {other_side} || ' to ' || H.location_label)"  # noqa: E501
            '))'
            ')))',
        )
        write_cursor.execute(  # solana fees and plain transfers naming the other side
            'UPDATE history_events SET notes=NULL WHERE identifier IN (SELECT H.identifier '
            'FROM history_events H JOIN chain_events_info C ON C.identifier=H.identifier WHERE '
            'H.entry_type=9 AND ('  # solana event
            "(H.type='spend' AND H.subtype='fee' AND C.counterparty='gas' AND H.notes='Spend ' || H.amount || ' SOL as transaction fee') OR "  # noqa: E501
            "(((H.type IN ('spend', 'receive', 'transfer') AND H.subtype='none' AND C.counterparty IS NULL) OR "  # noqa: E501
            "(H.type='deposit' AND H.subtype='deposit asset' AND C.counterparty IS NOT NULL) OR "
            "(H.type='withdrawal' AND H.subtype='remove asset' AND C.counterparty IS NOT NULL)"
            f") AND H.notes GLOB {verb} || ' ' || H.amount || ' * ' || CASE WHEN {outgoing} THEN 'to' ELSE 'from' END || ' ' || {other_side})"  # noqa: E501
            '))',
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
