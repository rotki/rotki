from typing import TYPE_CHECKING, Callable, List

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.constants import ZERO_ADDRESS
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.modules.yearn.constants import CPT_YEARN_V1, CPT_YEARN_V2
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import YEARN_VAULTS_V1_PROTOCOL, YEARN_VAULTS_V2_PROTOCOL, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

YEARN_DEPOSIT_4_BYTES = b'\xb6\xb5_%'
YEARN_WITHDRAW_4_BYTES = b'.\x1a}M'


def _get_vault_token_name(vault_address: 'ChecksumEvmAddress') -> str:
    try:
        vault_token = EvmToken(ethaddress_to_identifier(vault_address))
        vault_token_name = vault_token.name
    except (UnknownAsset, WrongAssetType):
        vault_token_name = str(vault_address)

    return vault_token_name


class YearnDecoder(DecoderInterface):
    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(ethereum_manager, base_tools, msg_aggregator)
        self.base_tools = base_tools
        vaults_v1 = GlobalDBHandler().get_ethereum_tokens(protocol=YEARN_VAULTS_V1_PROTOCOL)
        vaults_v2 = GlobalDBHandler().get_ethereum_tokens(protocol=YEARN_VAULTS_V2_PROTOCOL)
        self.vaults_v1 = {vault.evm_address for vault in vaults_v1}
        self.vaults_v2 = {vault.evm_address for vault in vaults_v2}

    def _maybe_enrich_yearn_transfers(
            self,
            token: 'EvmToken',  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,  # pylint: disable=unused-argument
            transaction: EvmTransaction,
            event: HistoryBaseEntry,
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> bool:
        counterparty = CPT_YEARN_V2
        if transaction.to_address in self.vaults_v1:
            counterparty = CPT_YEARN_V1
        elif transaction.to_address not in self.vaults_v2:
            return False

        is_deposit = False
        if transaction.input_data.startswith(YEARN_DEPOSIT_4_BYTES):
            is_deposit = True
        elif not transaction.input_data.startswith(YEARN_WITHDRAW_4_BYTES):
            # in this case is a method that we don't handle
            return False

        if (
            is_deposit is True and
            event.event_type == HistoryEventType.SPEND and
            event.counterparty == transaction.to_address
        ):
            event.event_type = HistoryEventType.DEPOSIT
            event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            event.counterparty = counterparty
            vault_token_name = _get_vault_token_name(transaction.to_address)
            event.notes = f'Deposit {event.balance.amount} {event.asset.resolve_to_crypto_asset().symbol} in {counterparty} vault {vault_token_name}'  # noqa: E501
        elif (
            is_deposit is True and
            event.event_type == HistoryEventType.RECEIVE and
            event.counterparty == ZERO_ADDRESS
        ):
            event.event_type = HistoryEventType.DEPOSIT
            event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
            event.counterparty = counterparty
            vault_token_name = _get_vault_token_name(transaction.to_address)
            event.notes = f'Recieve {event.balance.amount} {vault_token_name} after deposit in {counterparty}'  # noqa: E501
        elif (
            is_deposit is False and
            event.event_type == HistoryEventType.RECEIVE and
            event.counterparty == transaction.to_address
        ):
            event.event_type = HistoryEventType.WITHDRAWAL
            event.event_subtype = HistoryEventSubType.REMOVE_ASSET
            event.counterparty = counterparty
            vault_token_name = _get_vault_token_name(transaction.to_address)
            event.notes = f'Withdraw {event.balance.amount} {event.asset.resolve_to_crypto_asset().symbol} from {counterparty} vault {vault_token_name}'  # noqa: E501
        elif (
            is_deposit is False and
            event.event_type == HistoryEventType.SPEND and
            event.counterparty == ZERO_ADDRESS
        ):
            event.event_type = HistoryEventType.WITHDRAWAL
            event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
            event.counterparty = counterparty
            event.notes = f'Return {event.balance.amount} {event.asset.resolve_to_crypto_asset().symbol} to the {counterparty} vault'  # noqa: E501
        else:
            return False

        return True

    # -- DecoderInterface methods

    def enricher_rules(self) -> List[Callable]:
        return [
            self._maybe_enrich_yearn_transfers,
        ]

    def counterparties(self) -> List[str]:
        return [CPT_YEARN_V2, CPT_YEARN_V1]
