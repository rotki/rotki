import logging
from typing import TYPE_CHECKING

from rotkehlchen.globaldb.handler import GlobalDBHandler
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
        other columns. Null every stored note that equals the text rotki generated for it,
        matching the templates of the decoders of this version. Any other note, be it edited by
        the user, extended by a protocol decoder or written with a symbol the asset no longer
        has, stays stored.

        The asset symbols the decoders wrote into the notes are only in the global DB, so they
        are copied into a temporary table for the exact comparison.
        """
        write_cursor.execute(  # staking event notes were never read back from the DB
            'UPDATE history_events SET notes=NULL WHERE entry_type IN (3, 4, 5)',  # withdrawal, block, deposit  # noqa: E501
        )
        user_assets = {row[0] for row in write_cursor.execute('SELECT identifier FROM assets')}
        with GlobalDBHandler().conn.read_ctx() as global_cursor:
            symbols = [
                (identifier, symbol) for identifier, symbol in global_cursor.execute(
                    'SELECT A.identifier, COALESCE(C.symbol, A.name) FROM assets AS A '
                    'LEFT JOIN common_asset_details AS C ON A.identifier=C.identifier',
                ) if identifier in user_assets and symbol is not None
            ]
        write_cursor.execute('CREATE TEMP TABLE asset_symbols(identifier TEXT PRIMARY KEY COLLATE NOCASE, symbol TEXT NOT NULL)')  # noqa: E501
        write_cursor.executemany('INSERT OR IGNORE INTO asset_symbols VALUES (?, ?)', symbols)
        evm_basics = (
            'FROM history_events H JOIN chain_events_info C ON C.identifier=H.identifier '
            'JOIN asset_symbols S ON S.identifier=H.asset WHERE H.entry_type=2 AND ('  # evm event
        )
        write_cursor.execute(
            'UPDATE history_events SET notes=NULL WHERE identifier IN (SELECT H.identifier '
            f'{evm_basics}'
            "(H.subtype='fee' AND C.counterparty='gas' AND ("
            "(H.type='spend' AND H.notes='Burn ' || H.amount || ' ' || S.symbol || ' for gas') OR "
            "(H.type='fail' AND H.notes='Burn ' || H.amount || ' ' || S.symbol || ' for gas of a failed transaction')"  # noqa: E501
            ')) OR '
            "(H.type='informational' AND H.subtype='approve' AND C.counterparty IS NULL AND ("
            "(H.amount='0' AND H.notes='Revoke ' || S.symbol || ' spending approval of ' || H.location_label || ' by ' || C.address) OR "  # noqa: E501
            "(H.amount!='0' AND H.notes='Set ' || S.symbol || ' spending approval of ' || H.location_label || ' by ' || C.address || ' to ' || H.amount)"  # noqa: E501
            ')) OR '
            "(H.type='deploy' AND H.notes='Deploy a new contract at ' || C.address) OR "
            "(H.type='transaction to self' AND H.subtype='none' AND ("
            "(H.amount='0' AND H.notes='No value transaction to self') OR "
            "(H.amount!='0' AND H.notes='Transaction to self of ' || H.amount || ' ' || S.symbol)"
            '))'
            '))',
        )
        # Plain transfers. The verb and preposition follow the type. Native asset transfers
        # name only the other side, token transfers both. The location codes and native asset
        # identifiers are those of the EVM chains with transactions at this version.
        verb = "CASE H.type WHEN 'spend' THEN 'Send' WHEN 'receive' THEN 'Receive' WHEN 'transfer' THEN 'Transfer' WHEN 'deposit' THEN 'Deposit' ELSE 'Withdraw' END"  # noqa: E501
        outgoing = "H.type IN ('spend', 'transfer', 'deposit')"
        other_side = 'COALESCE(C.counterparty, C.address)'
        amount_and_symbol = "H.amount || ' ' || S.symbol"
        native_asset = (
            "((H.location IN ('f', 'g', 'i', 'j', 'n', 'o', char(127)) AND H.asset='ETH') OR "  # ethereum, optimism, arbitrum, base, scroll, zksync lite, robinhood  # noqa: E501
            "(H.location='h' AND H.asset='eip155:137/erc20:0x0000000000000000000000000000000000001010') OR "  # polygon  # noqa: E501
            "(H.location='k' AND H.asset='XDAI') OR (H.location='v' AND H.asset='BNB') OR "  # gnosis, bsc  # noqa: E501
            "(H.location='y' AND H.asset='HYPE') OR (H.location='z' AND H.asset='MON') OR "  # hyperliquid, monad  # noqa: E501
            "(H.location='~' AND H.asset='S'))"  # sonic
        )
        write_cursor.execute(
            'UPDATE history_events SET notes=NULL WHERE identifier IN (SELECT H.identifier '
            f'{evm_basics}'
            "((H.type IN ('spend', 'receive', 'transfer') AND H.subtype='none' AND C.counterparty IS NULL) OR "  # noqa: E501
            "(H.type='deposit' AND H.subtype='deposit asset' AND C.counterparty IS NOT NULL) OR "
            "(H.type='withdrawal' AND H.subtype='remove asset' AND C.counterparty IS NOT NULL)"
            ') AND ('
            f"({native_asset} AND H.notes={verb} || ' ' || {amount_and_symbol} || ' ' || CASE WHEN {outgoing} THEN 'to' ELSE 'from' END || ' ' || {other_side}) OR "  # noqa: E501
            f"(NOT {native_asset} AND H.asset NOT LIKE '%/erc721:%' AND ("
            f"({outgoing} AND H.notes={verb} || ' ' || {amount_and_symbol} || ' from ' || H.location_label || ' to ' || {other_side}) OR "  # noqa: E501
            f"(NOT {outgoing} AND H.notes={verb} || ' ' || {amount_and_symbol} || ' from ' || {other_side} || ' to ' || H.location_label)"  # noqa: E501
            '))'
            ')))',
        )
        write_cursor.execute(  # solana fees and plain transfers naming the other side
            'UPDATE history_events SET notes=NULL WHERE identifier IN (SELECT H.identifier '
            'FROM history_events H JOIN chain_events_info C ON C.identifier=H.identifier '
            'JOIN asset_symbols S ON S.identifier=H.asset WHERE H.entry_type=9 AND ('  # solana event  # noqa: E501
            "(H.type='spend' AND H.subtype='fee' AND C.counterparty='gas' AND H.notes='Spend ' || H.amount || ' SOL as transaction fee') OR "  # noqa: E501
            "(((H.type IN ('spend', 'receive', 'transfer') AND H.subtype='none' AND C.counterparty IS NULL) OR "  # noqa: E501
            "(H.type='deposit' AND H.subtype='deposit asset' AND C.counterparty IS NOT NULL) OR "
            "(H.type='withdrawal' AND H.subtype='remove asset' AND C.counterparty IS NOT NULL)"
            f") AND H.notes={verb} || ' ' || {amount_and_symbol} || ' ' || CASE WHEN {outgoing} THEN 'to' ELSE 'from' END || ' ' || {other_side})"  # noqa: E501
            '))',
        )
        write_cursor.execute('DROP TABLE asset_symbols')

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
