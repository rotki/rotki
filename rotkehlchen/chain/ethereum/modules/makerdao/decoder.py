from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.ethereum.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.defi.defisaver_proxy import HasDSProxy
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.constants.assets import (
    A_AAVE,
    A_BAL,
    A_BAT,
    A_COMP,
    A_DAI,
    A_ETH,
    A_GUSD,
    A_KNC,
    A_LINK,
    A_LRC,
    A_MANA,
    A_MATIC,
    A_PAX,
    A_RENBTC,
    A_SAI,
    A_TUSD,
    A_UNI,
    A_USDC,
    A_USDT,
    A_WBTC,
    A_YFI,
    A_ZRX,
)
from rotkehlchen.constants.ethereum import (
    MAKERDAO_AAVE_A_JOIN,
    MAKERDAO_BAL_A_JOIN,
    MAKERDAO_BAT_A_JOIN,
    MAKERDAO_CDP_MANAGER,
    MAKERDAO_COMP_A_JOIN,
    MAKERDAO_DAI_JOIN,
    MAKERDAO_ETH_A_JOIN,
    MAKERDAO_ETH_B_JOIN,
    MAKERDAO_ETH_C_JOIN,
    MAKERDAO_GUSD_A_JOIN,
    MAKERDAO_KNC_A_JOIN,
    MAKERDAO_LINK_A_JOIN,
    MAKERDAO_LRC_A_JOIN,
    MAKERDAO_MANA_A_JOIN,
    MAKERDAO_MATIC_A_JOIN,
    MAKERDAO_PAXUSD_A_JOIN,
    MAKERDAO_POT,
    MAKERDAO_RENBTC_A_JOIN,
    MAKERDAO_TUSD_A_JOIN,
    MAKERDAO_UNI_A_JOIN,
    MAKERDAO_USDC_A_JOIN,
    MAKERDAO_USDC_B_JOIN,
    MAKERDAO_USDT_A_JOIN,
    MAKERDAO_WBTC_A_JOIN,
    MAKERDAO_WBTC_B_JOIN,
    MAKERDAO_WBTC_C_JOIN,
    MAKERDAO_YFI_A_JOIN,
    MAKERDAO_ZRX_A_JOIN,
    RAY_DIGITS,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, Location
from rotkehlchen.utils.misc import (
    hex_or_bytes_to_address,
    hex_or_bytes_to_int,
    shift_num_right_by,
    ts_sec_to_ms,
)

from .constants import CPT_DSR, CPT_MIGRATION, CPT_VAULT

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.user_messages import MessagesAggregator


GENERIC_JOIN = b';M\xa6\x9f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501
GENERIC_EXIT = b'\xefi;\xed\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501

POT_JOIN = b'\x04\x98x\xf3\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501
POT_EXIT = b'\x7f\x86a\xa1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501

NEWCDP = b"\xd6\xbe\x0b\xc1xe\x8a8/\xf4\xf9\x1c\x8ch\xb5B\xaakqh[\x8f\xe4'\x96k\x87t\\>\xa7\xa2"
CDPMANAGER_MOVE = b'\xf9\xf3\r\xb6\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501
CDPMANAGER_FROB = b'E\xe6\xbd\xcd\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # noqa: E501


class MakerdaoDecoder(DecoderInterface, HasDSProxy):  # lgtm[py/missing-call-to-init]
    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_manager: 'EthereumManager',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.base = base_tools
        HasDSProxy.__init__(
            self,
            ethereum_manager=ethereum_manager,
            database=self.base.database,
            premium=None,  # not used here
            msg_aggregator=msg_aggregator,
        )

    def _get_address_or_proxy(self, address: ChecksumEvmAddress) -> Optional[ChecksumEvmAddress]:
        if self.base.is_tracked(address):
            return address

        # not directly from our account. Proxy?
        self._get_accounts_having_proxy()
        proxy_owner = self.proxy_to_address.get(address)
        if proxy_owner is not None and self.base.is_tracked(proxy_owner):
            return proxy_owner

        return None

    def _get_vault_details(
            self,
            cdp_id: int,
    ) -> Tuple[ChecksumEvmAddress, ChecksumEvmAddress]:
        """
        Queries the CDPManager to get the CDP details.
        Returns a tuple with the CDP address and the CDP owner as of the
        time of this call.

        May raise:
        - RemoteError if query to the node failed
        - DeserializationError if the query returns unexpected output
        """
        output = self.ethereum.multicall(
            calls=[(
                MAKERDAO_CDP_MANAGER.address,
                MAKERDAO_CDP_MANAGER.encode(method_name='urns', arguments=[cdp_id]),
            ), (
                MAKERDAO_CDP_MANAGER.address,
                MAKERDAO_CDP_MANAGER.encode(method_name='owns', arguments=[cdp_id]),
            )],
        )
        mapping = {}
        for result_encoded, method_name in zip(output, ('urns', 'owns')):
            result = MAKERDAO_CDP_MANAGER.decode(    # pylint: disable=unsubscriptable-object
                result_encoded,
                method_name,
                arguments=[cdp_id],
            )[0]
            if int(result, 16) == 0:
                raise DeserializationError('Could not deserialize {result} as address}')

            address = deserialize_evm_address(result)
            mapping[method_name] = address

        return mapping['urns'], mapping['owns']

    def decode_makerdao_vault_action(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
            vault_asset: CryptoAsset,
            vault_type: str,
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] == GENERIC_JOIN:
            raw_amount = hex_or_bytes_to_int(tx_log.topics[3])
            amount = asset_normalized_value(
                amount=raw_amount,
                asset=vault_asset,
            )
            # Go through decoded events to find and edit the transfer event
            for event in decoded_events:
                if event.event_type == HistoryEventType.SPEND and event.asset == vault_asset and event.balance.amount == amount:  # noqa: E501
                    event.sequence_index = tx_log.log_index  # to better position it in the list
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.counterparty = CPT_VAULT
                    event.notes = f'Deposit {amount} {vault_asset.symbol} to {vault_type} MakerDAO vault'  # noqa: E501
                    event.extra_data = {'vault_type': vault_type}
                    return None, None

        elif tx_log.topics[0] == GENERIC_EXIT:
            raw_amount = hex_or_bytes_to_int(tx_log.topics[3])
            amount = asset_normalized_value(
                amount=raw_amount,
                asset=vault_asset,
            )

            # Go through decoded events to find and edit the transfer event
            for event in decoded_events:
                if event.event_type == HistoryEventType.RECEIVE and event.asset == vault_asset and event.balance.amount == amount:  # noqa: E501
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_VAULT
                    event.notes = f'Withdraw {amount} {vault_asset.symbol} from {vault_type} MakerDAO vault'  # noqa: E501
                    event.extra_data = {'vault_type': vault_type}
                    return None, None

        return None, None

    def decode_makerdao_debt_payback(  # pylint: disable=no-self-use
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] == GENERIC_JOIN:
            join_user_address = hex_or_bytes_to_address(tx_log.topics[2])
            raw_amount = hex_or_bytes_to_int(tx_log.topics[3])
            amount = token_normalized_value(
                token_amount=raw_amount,
                token=A_DAI.resolve_to_evm_token(),
            )
            # The transfer comes right before, but we don't have enough information
            # yet to make sure that this transfer is indeed a vault payback debt. We
            # need to get a cdp frob event and compare vault id to address matches
            action_item = ActionItem(
                action='transform',
                sequence_index=tx_log.log_index,
                from_event_type=HistoryEventType.SPEND,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=A_DAI.resolve_to_evm_token(),
                amount=amount,
                to_event_subtype=HistoryEventSubType.PAYBACK_DEBT,
                to_counterparty=CPT_VAULT,
                extra_data={'vault_address': join_user_address},
            )
            return None, action_item

        return None, None

    def decode_pot_for_dsr(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] == POT_JOIN:
            potjoin_user_address = hex_or_bytes_to_address(tx_log.topics[1])
            user = self._get_address_or_proxy(potjoin_user_address)
            if user is None:
                return None, None

            # Now gotta find the DAI join event to get actual DAI value
            daijoin_log = None
            for event_log in all_logs:
                if event_log.address == MAKERDAO_DAI_JOIN.address and event_log.topics[0] == GENERIC_JOIN:  # noqa: E501
                    daijoin_user_address = hex_or_bytes_to_address(event_log.topics[1])
                    if daijoin_user_address != potjoin_user_address:
                        continue  # not a match

                    daijoin_log = event_log
                    break

            if daijoin_log is None:
                return None, None  # no matching daijoin for potjoin

            raw_amount = hex_or_bytes_to_int(daijoin_log.topics[3])
            amount = token_normalized_value(
                token_amount=raw_amount,
                token=A_DAI.resolve_to_evm_token(),
            )

            # The transfer event should be right before
            for event in decoded_events:
                if event.asset == A_DAI and event.event_type == HistoryEventType.SPEND and event.balance.amount == amount:  # noqa: E501
                    # found the event
                    event.location_label = user
                    event.counterparty = CPT_DSR
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.notes = f'Deposit {amount} DAI in the DSR'
                    return None, None

        elif tx_log.topics[0] == POT_EXIT:
            pot_exit_address = hex_or_bytes_to_address(tx_log.topics[1])
            user = self._get_address_or_proxy(pot_exit_address)
            if user is None:
                return None, None

            # Now gotta find the DAI exit event to get actual DAI value
            daiexit_log = None
            for event_log in all_logs:
                if event_log.address == MAKERDAO_DAI_JOIN.address and event_log.topics[0] == GENERIC_EXIT:  # noqa: E501
                    daiexit_user_address = hex_or_bytes_to_address(event_log.topics[2])
                    if daiexit_user_address != user:
                        continue  # not a match

                    daiexit_log = event_log
                    break

            if daiexit_log is None:
                return None, None  # no matching daiexit for potexit

            raw_amount = hex_or_bytes_to_int(daiexit_log.topics[3])
            amount = token_normalized_value(
                token_amount=raw_amount,
                token=A_DAI.resolve_to_evm_token(),
            )
            # The transfer event will be in a subsequent logs
            action_item = ActionItem(
                action='transform',
                sequence_index=tx_log.log_index,
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=A_DAI.resolve_to_evm_token(),
                amount=amount,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.REMOVE_ASSET,
                to_notes=f'Withdraw {amount} DAI from the DSR',
                to_counterparty=CPT_DSR,
            )
            return None, action_item

        return None, None

    def decode_proxy_creation(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] == b'%\x9b0\xca9\x88\\m\x80\x1a\x0b]\xbc\x98\x86@\xf3\xc2^/7S\x1f\xe18\xc5\xc5\xaf\x89U\xd4\x1b':  # noqa: E501
            owner_address = hex_or_bytes_to_address(tx_log.topics[2])
            if not self.base.is_tracked(owner_address):
                return None, None

            proxy_address = hex_or_bytes_to_address(tx_log.data[0:32])
            notes = f'Create DSR proxy {proxy_address} with owner {owner_address}'
            event = HistoryBaseEntry(
                event_identifier=transaction.tx_hash,
                sequence_index=self.base.get_sequence_index(tx_log),
                timestamp=ts_sec_to_ms(transaction.timestamp),
                location=Location.BLOCKCHAIN,
                location_label=owner_address,
                # TODO: This should be null for proposals and other informational events
                asset=A_ETH,
                balance=Balance(),
                notes=notes,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.DEPLOY,
                counterparty=proxy_address,
            )
            return event, None

        return None, None

    def _decode_vault_creation(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        owner_address = self._get_address_or_proxy(hex_or_bytes_to_address(tx_log.topics[2]))
        if owner_address is None:
            return None, None

        if not self.base.is_tracked(owner_address):
            return None, None

        cdp_id = hex_or_bytes_to_int(tx_log.topics[3])
        notes = f'Create MakerDAO vault with id {cdp_id} and owner {owner_address}'
        event = HistoryBaseEntry(
            event_identifier=transaction.tx_hash,
            sequence_index=self.base.get_sequence_index(tx_log),
            timestamp=ts_sec_to_ms(transaction.timestamp),
            location=Location.BLOCKCHAIN,
            location_label=owner_address,
            # TODO: This should be null for proposals and other informational events
            asset=A_ETH,
            balance=Balance(),
            notes=notes,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DEPLOY,
            counterparty='makerdao vault',
        )
        return event, None

    def _decode_vault_debt_generation(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        """Decode vault debt generation by parsing a lognote for cdpmanager move"""
        cdp_id = hex_or_bytes_to_int(tx_log.topics[2])
        destination = hex_or_bytes_to_address(tx_log.topics[3])

        owner = self._get_address_or_proxy(destination)
        if owner is None:
            return None, None

        # now we need to get the rad and since it's the 3rd argument its not in the indexed topics
        # but it's part of the data location after the first 132 bytes.
        # also need to shift by ray since it's in rad
        raw_amount = shift_num_right_by(hex_or_bytes_to_int(tx_log.data[132:164]), RAY_DIGITS)
        amount = token_normalized_value(
            token_amount=raw_amount,
            token=A_DAI.resolve_to_evm_token(),
        )

        # The transfer event appears after the debt generation event, so we need to transform it
        action_item = ActionItem(
            action='transform',
            sequence_index=tx_log.log_index,
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=A_DAI.resolve_to_evm_token(),
            amount=amount,
            to_event_type=HistoryEventType.WITHDRAWAL,
            to_event_subtype=HistoryEventSubType.GENERATE_DEBT,
            to_counterparty=CPT_VAULT,
            to_notes=f'Generate {amount} DAI from MakerDAO vault {cdp_id}',
            extra_data={'cdp_id': cdp_id},
        )
        return None, action_item

    def _decode_vault_change(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        """Decode CDPManger Frob (vault change)

        Used to find the vault id of a collateral deposit
        """
        cdp_id = hex_or_bytes_to_int(tx_log.topics[2])
        dink = hex_or_bytes_to_int(tx_log.topics[3])

        action_item = None
        for item in action_items:
            if item.extra_data and 'vault_address' in item.extra_data:
                action_item = item
                break

        if action_item is not None:
            # this concerns a vault debt payback. Checking only if CDP matches since
            # the owner response is at the time of the call and may have changed
            cdp_address, _ = self._get_vault_details(cdp_id)
            if cdp_address != action_item.extra_data['vault_address']:  # type: ignore
                return None, None  # vault address does not match

            # now find the payback transfer and transform it
            for event in decoded_events:
                if event.event_type == action_item.from_event_type and event.event_subtype == action_item.from_event_subtype and event.asset == action_item.asset and event.balance.amount == action_item.amount:  # noqa: E501
                    if action_item.to_event_type:
                        event.event_type = action_item.to_event_type
                    if action_item.to_event_subtype:
                        event.event_subtype = action_item.to_event_subtype
                    if action_item.to_counterparty:
                        event.counterparty = action_item.to_counterparty
                    if action_item.extra_data:
                        event.extra_data = action_item.extra_data
                        event.extra_data['cdp_id'] = cdp_id

                    event.notes = f'Payback {event.balance.amount} DAI of debt to makerdao vault {cdp_id}'  # noqa: E501
                    break

        else:  # collateral deposit
            # dink is the raw collateral amount change. Let's use this event to see if
            # there was a deposit event beforehand to append the cdp id
            for event in decoded_events:
                crypto_asset = event.asset.resolve_to_crypto_asset()
                if event.event_type == HistoryEventType.DEPOSIT and event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET and event.counterparty == CPT_VAULT:  # noqa: E501
                    normalized_dink = asset_normalized_value(
                        amount=dink,
                        asset=event.asset.resolve_to_crypto_asset(),
                    )
                    if normalized_dink != event.balance.amount:
                        continue

                    vault_type = event.extra_data.get('vault_type', 'unknown') if event.extra_data else 'unknown'  # noqa: E501
                    event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} to {vault_type} vault {cdp_id}'  # noqa: E501
                    break

        return None, None

    def decode_cdp_manager_events(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] == NEWCDP:
            return self._decode_vault_creation(tx_log=tx_log, transaction=transaction, decoded_events=decoded_events, all_logs=all_logs)  # noqa: E501
        if tx_log.topics[0] == CDPMANAGER_MOVE:
            return self._decode_vault_debt_generation(tx_log=tx_log, transaction=transaction, decoded_events=decoded_events, all_logs=all_logs)  # noqa: E501
        if tx_log.topics[0] == CDPMANAGER_FROB:
            return self._decode_vault_change(tx_log=tx_log, transaction=transaction, decoded_events=decoded_events, all_logs=all_logs, action_items=action_items)  # noqa: E501

        return None, None

    def decode_saidai_migration(
            self,
            tx_log: EthereumTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: List[HistoryBaseEntry],  # pylint: disable=unused-argument
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER:
            to_address = hex_or_bytes_to_address(tx_log.topics[2])
            if to_address != '0xc73e0383F3Aff3215E6f04B0331D58CeCf0Ab849':
                return None, None

            # sending SAI to migration contract
            transfer = self.base.decode_erc20_721_transfer(token=A_SAI.resolve_to_evm_token(), tx_log=tx_log, transaction=transaction)  # noqa: E501
            if transfer is None:
                return None, None

            transfer.event_type = HistoryEventType.MIGRATE
            transfer.event_subtype = HistoryEventSubType.SPEND
            transfer.notes = f'Migrate {transfer.balance.amount} SAI to DAI'
            transfer.counterparty = CPT_MIGRATION

            # also create action item for the receive transfer
            action_item = ActionItem(
                action='transform',
                sequence_index=tx_log.log_index,
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=A_DAI.resolve_to_evm_token(),
                amount=transfer.balance.amount,
                to_event_type=HistoryEventType.MIGRATE,
                to_event_subtype=HistoryEventSubType.RECEIVE,
                to_notes=f'Receive {transfer.balance.amount} DAI from SAI->DAI migration',
                to_counterparty='makerdao migration',
            )
            return transfer, action_item

        return None, None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEvmAddress, Tuple[Any, ...]]:
        return {
            MAKERDAO_BAT_A_JOIN.address: (self.decode_makerdao_vault_action, A_BAT, 'BAT-A'),
            MAKERDAO_ETH_A_JOIN.address: (self.decode_makerdao_vault_action, A_ETH, 'ETH-A'),
            MAKERDAO_ETH_B_JOIN.address: (self.decode_makerdao_vault_action, A_ETH, 'ETH-B'),
            MAKERDAO_ETH_C_JOIN.address: (self.decode_makerdao_vault_action, A_ETH, 'ETH-C'),
            MAKERDAO_KNC_A_JOIN.address: (self.decode_makerdao_vault_action, A_KNC, 'KNC-A'),
            MAKERDAO_TUSD_A_JOIN.address: (self.decode_makerdao_vault_action, A_TUSD, 'TUSD-A'),
            MAKERDAO_USDC_A_JOIN.address: (self.decode_makerdao_vault_action, A_USDC, 'USDC-A'),
            MAKERDAO_USDC_B_JOIN.address: (self.decode_makerdao_vault_action, A_USDC, 'USDC-B'),
            MAKERDAO_USDT_A_JOIN.address: (self.decode_makerdao_vault_action, A_USDT, 'USDT-A'),
            MAKERDAO_WBTC_A_JOIN.address: (self.decode_makerdao_vault_action, A_WBTC, 'WBTC-A'),
            MAKERDAO_WBTC_B_JOIN.address: (self.decode_makerdao_vault_action, A_WBTC, 'WBTC-B'),
            MAKERDAO_WBTC_C_JOIN.address: (self.decode_makerdao_vault_action, A_WBTC, 'WBTC-C'),
            MAKERDAO_ZRX_A_JOIN.address: (self.decode_makerdao_vault_action, A_ZRX, 'ZRX-A'),
            MAKERDAO_MANA_A_JOIN.address: (self.decode_makerdao_vault_action, A_MANA, 'MANA-A'),
            MAKERDAO_PAXUSD_A_JOIN.address: (self.decode_makerdao_vault_action, A_PAX, 'PAXUSD-A'),
            MAKERDAO_COMP_A_JOIN.address: (self.decode_makerdao_vault_action, A_COMP, 'COMP-A'),
            MAKERDAO_LRC_A_JOIN.address: (self.decode_makerdao_vault_action, A_LRC, 'LRC-A'),
            MAKERDAO_LINK_A_JOIN.address: (self.decode_makerdao_vault_action, A_LINK, 'LINK-A'),
            MAKERDAO_BAL_A_JOIN.address: (self.decode_makerdao_vault_action, A_BAL, 'BAL-A'),
            MAKERDAO_YFI_A_JOIN.address: (self.decode_makerdao_vault_action, A_YFI, 'YFI-A'),
            MAKERDAO_GUSD_A_JOIN.address: (self.decode_makerdao_vault_action, A_GUSD, 'GUSD-A'),
            MAKERDAO_UNI_A_JOIN.address: (self.decode_makerdao_vault_action, A_UNI, 'UNI-A'),
            MAKERDAO_RENBTC_A_JOIN.address: (self.decode_makerdao_vault_action, A_RENBTC, 'RENBTC-A'),  # noqa: E501
            MAKERDAO_AAVE_A_JOIN.address: (self.decode_makerdao_vault_action, A_AAVE, 'AAVE-A'),
            MAKERDAO_MATIC_A_JOIN.address: (self.decode_makerdao_vault_action, A_MATIC, 'MATIC-A'),
            MAKERDAO_POT.address: (self.decode_pot_for_dsr,),
            MAKERDAO_DAI_JOIN.address: (self.decode_makerdao_debt_payback,),
            string_to_evm_address('0xA26e15C895EFc0616177B7c1e7270A4C7D51C997'): (self.decode_proxy_creation,),  # noqa: E501
            string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'): (self.decode_saidai_migration,),  # noqa: E501
            MAKERDAO_CDP_MANAGER.address: (self.decode_cdp_manager_events,),
        }

    def counterparties(self) -> List[str]:
        return [CPT_VAULT, CPT_DSR, CPT_MIGRATION]
