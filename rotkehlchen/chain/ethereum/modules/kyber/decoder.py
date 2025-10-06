from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.kyber.constants import CPT_KYBER, KYBER_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.kyber.decoder import (
    KYBER_AGGREGATOR_CONTRACT,
    KyberCommonDecoder,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_KYBER_LEGACY

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

KYBER_TRADE_LEGACY = b'\xf7$\xb4\xdff\x17G6\x12\xb5=\x7f\x88\xec\xc6\xea\x980t\xb3\t`\xa0I\xfc\xd0e\x7f\xfe\x80\x80\x83'  # noqa: E501
KYBER_TRADE = b"\xd3\x0c\xa3\x99\xcbCP~\xce\xc6\xa6)\xa3\\\xf4^\xb9\x8c\xdaU\x0c'im\xcb\r\x8cJ8s\xcel"  # noqa: E501
KYBER_LEGACY_CONTRACT = string_to_evm_address('0x9ae49C0d7F8F9EF4B864e004FE86Ac8294E20950')
KYBER_LEGACY_CONTRACT_MIGRATED = string_to_evm_address('0x65bF64Ff5f51272f729BDcD7AcFB00677ced86Cd')  # noqa: E501
KYBER_LEGACY_CONTRACT_UPGRADED = string_to_evm_address('0x9AAb3f75489902f3a48495025729a0AF77d4b11e')  # noqa: E501


class KyberDecoder(KyberCommonDecoder):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def _legacy_contracts_basic_info(self, tx_log: EvmTxReceiptLog) -> tuple[ChecksumEvmAddress, CryptoAsset, CryptoAsset]:  # noqa: E501
        """
        Returns:
        - address of the sender
        - source token (can be none)
        - destination token (can be none)
        May raise:
        - DeserializationError when using hex_or_bytes_to_address
        """
        sender = bytes_to_address(tx_log.topics[1])
        source_token_address = bytes_to_address(tx_log.data[:32])
        destination_token_address = bytes_to_address(tx_log.data[32:64])

        source_token = self.base.get_or_create_evm_asset(source_token_address)
        destination_token = self.base.get_or_create_evm_asset(destination_token_address)
        return sender, source_token, destination_token

    def _decode_legacy_trade(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != KYBER_TRADE:
            return DEFAULT_EVM_DECODING_OUTPUT

        sender, source_asset, destination_asset = self._legacy_contracts_basic_info(context.tx_log)
        spent_amount_raw = int.from_bytes(context.tx_log.data[64:96])
        return_amount_raw = int.from_bytes(context.tx_log.data[96:128])
        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_asset)
        return_amount = asset_normalized_value(amount=return_amount_raw, asset=destination_asset)
        self._maybe_update_events(
            decoded_events=context.decoded_events,
            sender=sender,
            source_asset=source_asset,
            destination_asset=destination_asset,
            spent_amount=spent_amount,
            return_amount=return_amount,
            counterparty=CPT_KYBER_LEGACY,
        )

        return EvmDecodingOutput(process_swaps=True)

    def _decode_legacy_upgraded_trade(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != KYBER_TRADE_LEGACY:
            return DEFAULT_EVM_DECODING_OUTPUT

        sender, source_asset, destination_asset = self._legacy_contracts_basic_info(context.tx_log)
        spent_amount_raw = int.from_bytes(context.tx_log.data[96:128])
        return_amount_raw = int.from_bytes(context.tx_log.data[128:160])
        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_asset)
        return_amount = asset_normalized_value(amount=return_amount_raw, asset=destination_asset)
        self._maybe_update_events(
            decoded_events=context.decoded_events,
            sender=sender,
            source_asset=source_asset,
            destination_asset=destination_asset,
            spent_amount=spent_amount,
            return_amount=return_amount,
            counterparty=CPT_KYBER_LEGACY,
        )

        return EvmDecodingOutput(process_swaps=True)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            KYBER_LEGACY_CONTRACT: (self._decode_legacy_trade,),
            KYBER_LEGACY_CONTRACT_MIGRATED: (self._decode_legacy_trade,),
            KYBER_LEGACY_CONTRACT_UPGRADED: (self._decode_legacy_upgraded_trade,),
            KYBER_AGGREGATOR_CONTRACT: (self._decode_aggregator_trade,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(identifier=CPT_KYBER_LEGACY, **KYBER_CPT_DETAILS),
            CounterpartyDetails(identifier=CPT_KYBER, **KYBER_CPT_DETAILS),
        )
