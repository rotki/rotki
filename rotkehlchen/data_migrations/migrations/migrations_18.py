import json
import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.chain.gnosis.modules.monerium.constants import (
    V1_TO_V2_MONERIUM_MAPPINGS as GNOSIS_MONERIUM_MAPPINGS,
)
from rotkehlchen.chain.polygon_pos.modules.monerium.constants import (
    V1_TO_V2_MONERIUM_MAPPINGS as POLYGON_MONERIUM_MAPPINGS,
)
from rotkehlchen.db.constants import EVMTX_SPAM
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.utils import set_token_spam_protocol
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SPAM_PROTOCOL, CacheType, Location
from rotkehlchen.utils.misc import address_to_bytes32
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def data_migration_18(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:  # pylint: disable=unused-argument
    """
    Introduced at v1.35.1

    - Fix the issue of extra transactions saved in the DB from the graph queries
    for delegation to arbitrum
    - Removes monerium tokens from spam
    """
    @progress_step(description='Cleaning up extra The Graph transactions.')
    def cleanup_extra_thegraph_txs(rotki: 'Rotkehlchen') -> None:
        dbevents = DBHistoryEvents(rotki.data.db)
        with rotki.data.db.conn.read_ctx() as cursor:
            tracked_addresses = rotki.data.db.get_evm_accounts(cursor)

        if len(tracked_addresses) == 0:
            return

        db_filter = EvmEventFilterQuery.make(
            counterparties=[CPT_THEGRAPH],
            location=Location.ETHEREUM,
            event_types=[HistoryEventType.INFORMATIONAL],
            event_subtypes=[HistoryEventSubType.APPROVE],
            location_labels=tracked_addresses,  # type: ignore  # sequence[address] == list[str]
            order_by_rules=[('timestamp', True)],  # order by timestamp in ascending order
        )
        with rotki.data.db.conn.read_ctx() as cursor:
            events = dbevents.get_history_events(
                cursor=cursor,
                filter_query=db_filter,
                has_premium=True,
            )
        approved_delegators = {x.address for x in events if x.address is not None}
        all_addresses = approved_delegators | set(tracked_addresses)

        tracked_placeholders = ','.join('?' * len(tracked_addresses))
        delegators_placeholders = ','.join('?' * len(approved_delegators))
        all_placeholders = ','.join('?' * (len(approved_delegators) + len(tracked_addresses)))
        # Find all possible logs we need to keep for our related addresses and mark the transactions  # noqa: E501
        querystr = f"""SELECT DISTINCT et.tx_hash FROM evm_transactions et
    JOIN evmtx_receipts er ON et.identifier = er.tx_id
    JOIN evmtx_receipt_logs erl ON er.tx_id = erl.tx_id
    JOIN evmtx_receipt_log_topics erlt0 ON erl.identifier = erlt0.log
    JOIN evmtx_receipt_log_topics erlt2 ON erl.identifier = erlt2.log
    WHERE erl.address = '0xF55041E37E12cD407ad00CE2910B8269B01263b9'
      AND
        (erlt0.topic_index = 0  /* DelegationTransferredToL2 */
      AND erlt0.topic = X'231E5CFEFF7759A468241D939AB04A60D603B17E359057ABBB8F52AFC3E4986B'
    AND ((
         erlt2.topic_index = 2
         AND erlt2.topic IN ({tracked_placeholders}))"""
        query_bindings = [address_to_bytes32(x) for x in tracked_addresses]

        if len(approved_delegators) != 0:
            querystr += f' OR (erlt2.topic_index = 1 AND erlt2.topic IN({delegators_placeholders}))'  # noqa: E501
            query_bindings += [address_to_bytes32(x) for x in approved_delegators]

        querystr += f"""
        ))OR
        ((erlt0.topic_index = 0  /* StakeDelegationWithdrawn */
        AND erlt0.topic = X'1B2E7737E043C5CF1B587CEB4DAEB7AE00148B9BDA8F79F1093EEAD08F141952') AND (erlt2.topic_index = 2 AND erlt2.topic IN ({all_placeholders})))
        """  # noqa: E501
        query_bindings += [address_to_bytes32(x) for x in all_addresses]

        querystr += f"""
        OR
        ((erlt0.topic_index = 0  /* StakeDelegated */
        AND erlt0.topic = X'CD0366DCE5247D874FFC60A762AA7ABBB82C1695BBB171609C1B8861E279EB73') AND (erlt2.topic_index = 2 AND erlt2.topic IN ({all_placeholders})))
        """  # noqa: E501
        query_bindings += [address_to_bytes32(x) for x in all_addresses]

        querystr += f"""
        OR
        ((erlt0.topic_index = 0  /* StakeDelegatedLocked */
        AND erlt0.topic = X'0430183F84D9C4502386D499DA806543DEE1D9DE83C08B01E39A6D2116C43B25') AND (erlt2.topic_index = 2 AND erlt2.topic IN ({all_placeholders})))
        """  # noqa: E501
        query_bindings += [address_to_bytes32(x) for x in all_addresses]

        to_keep_hashes = []
        with rotki.data.db.conn.read_ctx() as cursor:
            cursor.execute(querystr, query_bindings)
            to_keep_hashes = [x[0] for x in cursor]

        # Finally delete the unneeded transactions
        query_bindings = []
        querystr = """DELETE FROM evm_transactions
        WHERE identifier IN (
        SELECT DISTINCT et.identifier
        FROM evm_transactions et
        JOIN evmtx_receipts er ON et.identifier = er.tx_id
        JOIN evmtx_receipt_logs erl ON er.tx_id = erl.tx_id
        WHERE erl.address = '0xF55041E37E12cD407ad00CE2910B8269B01263b9'
    ) AND tx_hash NOT IN (SELECT tx_hash from evm_events_info)"""
        if len(to_keep_hashes) != 0:
            # we have also performed a thorough logs query above in case some were not decoded.
            # As if the transactions were not decoded yet then the
            # tx_hash NOT IN (SELECT tx_hash from evm_events_info) won't help avoid
            # deleting important transactions
            to_keep_placeholders = ','.join('?' * len(to_keep_hashes))
            querystr += f' AND tx_hash NOT IN ({to_keep_placeholders})'
            query_bindings += to_keep_hashes

        with rotki.data.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(querystr, query_bindings)

        rotki.data.db.conn.execute('VACUUM;')  # also since this cleans up a lot of space vacuum

    @progress_step(description='Whitelisting monerium assets.')
    def whitelist_monerium_assets(rotki: 'Rotkehlchen') -> None:
        """Remove from the spam assets all the monerium tokens in
        gnosis and polygon
        """
        globaldb = GlobalDBHandler()
        tokens: set[EvmToken] = set()
        monerium_tokens = set(GNOSIS_MONERIUM_MAPPINGS.keys())
        monerium_tokens |= {new_asset.identifier for new_asset in GNOSIS_MONERIUM_MAPPINGS.values()}  # noqa: E501
        monerium_tokens |= set(POLYGON_MONERIUM_MAPPINGS.keys())
        monerium_tokens |= {new_asset.identifier for new_asset in POLYGON_MONERIUM_MAPPINGS.values()}  # noqa: E501
        monerium_tokens |= {  # ethereum tokens
            'eip155:1/erc20:0x3231Cb76718CDeF2155FC47b5286d82e6eDA273f',  # eure
            'eip155:1/erc20:0x7ba92741Bf2A568abC6f1D3413c58c6e0244F8fD',  # gbpe
            'eip155:1/erc20:0xBc5142e0CC5eB16b47c63B0f033d4c2480853a52',  # usde
            'eip155:1/erc20:0xC642549743A93674cf38D6431f75d6443F88E3E2',  # iske
        }
        for legacy_id in monerium_tokens:
            try:
                tokens.add(EvmToken(legacy_id))
            except UnknownAsset:
                log.error(f'Skipping unknown legacy monerium asset {legacy_id} at data migration 18')  # noqa: E501

        for token in tokens:
            with globaldb.conn.write_ctx() as write_cursor:
                globaldb_set_general_cache_values(  # add token to whitelist
                    write_cursor=write_cursor,
                    key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
                    values=(token.identifier,),
                )

                if token.protocol == SPAM_PROTOCOL:  # remove the spam protocol if it was set
                    set_token_spam_protocol(write_cursor=write_cursor, token=token, is_spam=False)

            with rotki.data.db.user_write() as write_cursor:  # remove it from the ignored assets  # noqa: E501
                rotki.data.db.remove_from_ignored_assets(
                    write_cursor=write_cursor,
                    asset=token,
                )

    @progress_step(description='Removing spam transactions.')
    def remove_spam_detection_on_transactions(rotki: 'Rotkehlchen') -> None:
        """We will remove any marked transaction as spam from the database so they can be decoded
        in case something went wrong with the autodetection of spam.
        """
        with rotki.data.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM evm_tx_mappings WHERE tx_id IN (SELECT tx_id FROM '
                'evm_tx_mappings WHERE value=?)',
                (EVMTX_SPAM,),
            )

    @progress_step(description='Removing manual current price oracle.')
    def _remove_manualcurrent_oracle(rotki: 'Rotkehlchen') -> None:
        """Removes the manualcurrent oracle from the current_price_oracles setting

        This had already happened in upgrade v41->v42 but the frontend still had the option to
        add it back and the backend was not rejecting it. So to be sure backend settings are clean
        we need to do it one more time here.
        """
        with rotki.data.db.conn.read_ctx() as cursor:
            cursor.execute("SELECT value FROM settings WHERE name='current_price_oracles'")
            if (data := cursor.fetchone()) is None:
                return  # oracles not configured

        try:
            oracles: list[str] = json.loads(data[0])
        except json.JSONDecodeError as e:
            log.error(f'Failed to read oracles from user db due to {e!s}. DB data was {data[0]}. Deleting setting ...')  # noqa: E501
            with rotki.data.db.user_write() as write_cursor:
                write_cursor.execute(
                    'DELETE FROM settings WHERE name=?', ('current_price_oracles',),
                )
                return

        with rotki.data.db.user_write() as write_cursor:
            write_cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                (
                    'current_price_oracles',
                    json.dumps([oracle for oracle in oracles if oracle != 'manualcurrent']),
                ),
            )

    @progress_step(description='Cleaning up Yearn cache.')
    def _remove_yearn_cache(rotki: 'Rotkehlchen') -> None:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            write_cursor.execute('DELETE FROM unique_cache WHERE key=?', ('YEARN_VAULTS',))

    # perform steps and Vacuum since we potentially delete lots of un-needed data
    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=True)
