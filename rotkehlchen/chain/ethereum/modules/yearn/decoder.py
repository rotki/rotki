from typing import TYPE_CHECKING, Callable

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.yearn.constants import CPT_YEARN_V1, CPT_YEARN_V2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import (
    YEARN_VAULTS_V1_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    ChainID,
    EvmTransaction,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
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
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        vaults_v1 = GlobalDBHandler().get_evm_tokens(chain_id=ChainID.ETHEREUM, protocol=YEARN_VAULTS_V1_PROTOCOL)  # noqa: E501
        vaults_v2 = GlobalDBHandler().get_evm_tokens(chain_id=ChainID.ETHEREUM, protocol=YEARN_VAULTS_V2_PROTOCOL)  # noqa: E501
        self.vaults_v1 = {vault.evm_address for vault in vaults_v1}
        self.vaults_v2 = {vault.evm_address for vault in vaults_v2}

    def _maybe_enrich_yearn_transfers(
            self,
            token: 'EvmToken',
            tx_log: EvmTxReceiptLog,  # pylint: disable=unused-argument
            transaction: EvmTransaction,
            event: HistoryBaseEntry,
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> bool:
        """
        Enrich ethereum transfers made during the execution of yearn contracts.
        This enricher detects:
        - deposits
        - withdrawals

        First we make sure that the contract is a yearn v1 or v2 contract and that the method
        executed in the contract is one of the expected.
        """
        counterparty = CPT_YEARN_V2
        if transaction.to_address in self.vaults_v1:
            counterparty = CPT_YEARN_V1
        elif transaction.to_address not in self.vaults_v2:
            return False

        is_deposit = False
        if transaction.input_data.startswith(YEARN_DEPOSIT_4_BYTES):
            is_deposit = True
        elif not transaction.input_data.startswith(YEARN_WITHDRAW_4_BYTES):
            # a yearn contract method that we don't need to handle
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
            event.notes = f'Deposit {event.balance.amount} {token.symbol} in {counterparty} vault {vault_token_name}'  # noqa: E501
        elif (
            is_deposit is True and
            event.event_type == HistoryEventType.RECEIVE and
            event.counterparty == ZERO_ADDRESS
        ):
            event.event_type = HistoryEventType.DEPOSIT
            event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
            event.counterparty = counterparty
            vault_token_name = _get_vault_token_name(transaction.to_address)
            event.notes = f'Receive {event.balance.amount} {vault_token_name} after deposit in a {counterparty} vault'  # noqa: E501
        elif (
            is_deposit is False and
            event.event_type == HistoryEventType.RECEIVE and
            event.counterparty == transaction.to_address
        ):
            event.event_type = HistoryEventType.WITHDRAWAL
            event.event_subtype = HistoryEventSubType.REMOVE_ASSET
            event.counterparty = counterparty
            vault_token_name = _get_vault_token_name(transaction.to_address)
            event.notes = f'Withdraw {event.balance.amount} {token.symbol} from {counterparty} vault {vault_token_name}'  # noqa: E501
        elif (
            is_deposit is False and
            event.event_type == HistoryEventType.SPEND and
            event.counterparty == ZERO_ADDRESS
        ):
            event.event_type = HistoryEventType.WITHDRAWAL
            event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
            event.counterparty = counterparty
            event.notes = f'Return {event.balance.amount} {token.symbol} to a {counterparty} vault'  # noqa: E501
        else:
            # in this case we failed to find a valid transfer event. Inform about the failure
            return False

        return True

    # -- DecoderInterface methods

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_yearn_transfers,
        ]

    def counterparties(self) -> list[str]:
        return [CPT_YEARN_V2, CPT_YEARN_V1]
