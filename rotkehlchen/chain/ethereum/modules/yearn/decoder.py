from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.yearn.constants import (
    CPT_YEARN_V1,
    CPT_YEARN_V2,
    CPT_YEARN_V3,
    YEARN_ICON,
    YEARN_LABEL_V1,
    YEARN_LABEL_V2,
    YEARN_LABEL_V3,
)
from rotkehlchen.chain.ethereum.modules.yearn.utils import query_yearn_vaults
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import (
    YEARN_VAULTS_V1_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    YEARN_VAULTS_V3_PROTOCOL,
    CacheType,
    ChainID,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

YEARN_DEPOSIT_AMOUNT_4_BYTES = b'\xd0\xe3\r\xb0'
YEARN_DEPOSIT_4_BYTES = b'\xb6\xb5_%'
YEARN_DEPOSIT_4_BYTES_V3 = b'\x6E\x55\x3F\x65'
YEARN_WITHDRAW_AMOUNT_4_BYTES = b'.\x1a}M'
YEARN_WITHDRAW_4_BYTES = b'<\xcf\xd6\x0b'
YEARN_WITHDRAW_4_BYTES_V3 = b'\x9f\x40\xa7\xb3'


def _get_vault_token_name(vault_address: 'ChecksumEvmAddress') -> str:
    try:
        vault_token = EvmToken(ethaddress_to_identifier(vault_address))
        vault_token_name = vault_token.name
    except (UnknownAsset, WrongAssetType):
        vault_token_name = str(vault_address)

    return vault_token_name


class YearnDecoder(DecoderInterface, ReloadableDecoderMixin):
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
        self.vaults: dict[str, set[ChecksumEvmAddress]] = {
            YEARN_VAULTS_V1_PROTOCOL: set(),
            YEARN_VAULTS_V2_PROTOCOL: set(),
        }

    def reload_data(self) -> None:
        """Check that cache is up to date and refresh cache from db"""
        if should_update_protocol_cache(CacheType.YEARN_VAULTS) is True:
            query_yearn_vaults(db=self.evm_inquirer.database)
        elif len(self.vaults[YEARN_VAULTS_V2_PROTOCOL]) != 0:
            return  # we didn't update the globaldb cache and we have the data already

        with GlobalDBHandler().conn.read_ctx() as cursor:
            query_body = 'FROM evm_tokens WHERE protocol IN (?, ?, ?) AND chain=?'
            bindings = (
                YEARN_VAULTS_V1_PROTOCOL,
                YEARN_VAULTS_V2_PROTOCOL,
                YEARN_VAULTS_V3_PROTOCOL,
                ChainID.ETHEREUM.serialize_for_db(),
            )
            cursor.execute(f'SELECT COUNT(*) {query_body}', bindings)
            if cursor.fetchone()[0] == len(self.vaults[YEARN_VAULTS_V3_PROTOCOL]) + len(self.vaults[YEARN_VAULTS_V2_PROTOCOL]) + len(self.vaults[YEARN_VAULTS_V1_PROTOCOL]):  # noqa: E501
                return  # up to date

            # we are missing new vaults. Populate the cache
            cursor.execute(f'SELECT protocol, address {query_body}', bindings)
            for row in cursor:
                self.vaults[row[0]].add(string_to_evm_address(row[1]))

    def _maybe_enrich_yearn_transfers(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        Enrich ethereum transfers made during the execution of yearn contracts.
        This enricher detects:
        - deposits
        - withdrawals

        First we make sure that the contract is a yearn v1, v2 or v3 contract and that the method
        executed in the contract is one of the expected.
        """
        if context.transaction.to_address is None:
            return FAILED_ENRICHMENT_OUTPUT

        protocol = CPT_YEARN_V3
        if context.transaction.to_address in self.vaults[YEARN_VAULTS_V1_PROTOCOL]:
            protocol = CPT_YEARN_V1
        elif context.transaction.to_address in self.vaults[YEARN_VAULTS_V2_PROTOCOL]:
            protocol = CPT_YEARN_V2
        elif context.transaction.to_address not in self.vaults[YEARN_VAULTS_V3_PROTOCOL]:
            return FAILED_ENRICHMENT_OUTPUT

        is_deposit = False
        if (
            context.transaction.input_data.startswith(YEARN_DEPOSIT_4_BYTES) or
            context.transaction.input_data.startswith(YEARN_DEPOSIT_AMOUNT_4_BYTES) or
            context.transaction.input_data.startswith(YEARN_DEPOSIT_4_BYTES_V3)
        ):
            is_deposit = True
        elif not (
            context.transaction.input_data.startswith(YEARN_WITHDRAW_4_BYTES) or
            context.transaction.input_data.startswith(YEARN_WITHDRAW_AMOUNT_4_BYTES) or
            context.transaction.input_data.startswith(YEARN_WITHDRAW_4_BYTES_V3)
        ):
            # a yearn contract method that we don't need to handle
            return FAILED_ENRICHMENT_OUTPUT

        if (
            is_deposit is True and
            context.event.event_type == HistoryEventType.SPEND and
            context.event.address == context.transaction.to_address
        ):
            context.event.event_type = HistoryEventType.DEPOSIT
            context.event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            context.event.counterparty = protocol
            vault_token_name = _get_vault_token_name(context.transaction.to_address)
            context.event.notes = f'Deposit {context.event.balance.amount} {context.token.symbol} in {protocol} vault {vault_token_name}'  # noqa: E501
        elif (
            is_deposit is True and
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.address == ZERO_ADDRESS
        ):
            context.event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
            context.event.counterparty = protocol
            vault_token_name = _get_vault_token_name(context.transaction.to_address)
            context.event.notes = f'Receive {context.event.balance.amount} {vault_token_name} after deposit in a {protocol} vault'  # noqa: E501
        elif (
            is_deposit is False and
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.address == context.transaction.to_address
        ):
            context.event.event_type = HistoryEventType.WITHDRAWAL
            context.event.event_subtype = HistoryEventSubType.REMOVE_ASSET
            context.event.counterparty = protocol
            vault_token_name = _get_vault_token_name(context.transaction.to_address)
            context.event.notes = f'Withdraw {context.event.balance.amount} {context.token.symbol} from {protocol} vault {vault_token_name}'  # noqa: E501
        elif (
            is_deposit is False and
            context.event.event_type == HistoryEventType.SPEND and
            context.event.address == ZERO_ADDRESS
        ):
            context.event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
            context.event.counterparty = protocol
            context.event.notes = f'Return {context.event.balance.amount} {context.token.symbol} to a {protocol} vault'  # noqa: E501
        else:
            # in this case we failed to find a valid transfer event. Inform about the failure
            return FAILED_ENRICHMENT_OUTPUT

        return TransferEnrichmentOutput(matched_counterparty=protocol)

    # -- DecoderInterface methods

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_yearn_transfers,
        ]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(identifier=CPT_YEARN_V1, label=YEARN_LABEL_V1, image=YEARN_ICON),
            CounterpartyDetails(identifier=CPT_YEARN_V2, label=YEARN_LABEL_V2, image=YEARN_ICON),
            CounterpartyDetails(identifier=CPT_YEARN_V3, label=YEARN_LABEL_V3, image=YEARN_ICON),
        )
