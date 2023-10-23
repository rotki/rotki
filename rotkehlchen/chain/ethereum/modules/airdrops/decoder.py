import logging
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.convex.constants import CONVEX_CPT_DETAILS
from rotkehlchen.chain.ethereum.modules.uniswap.constants import UNISWAP_ICON, UNISWAP_LABEL
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.airdrops import match_airdrop_claim
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.cowswap.constants import COWSWAP_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.cowswap.interfaces import CowswapAirdropDecoder
from rotkehlchen.chain.evm.decoding.oneinch.constants import ONEINCH_ICON, ONEINCH_LABEL
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_BADGER,
    A_CVX,
    A_ELFI,
    A_FOX,
    A_FPIS,
    A_UNI,
    A_VCOW,
)
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import (
    CPT_BADGER,
    CPT_CONVEX,
    CPT_ELEMENT_FINANCE,
    CPT_FRAX,
    CPT_ONEINCH,
    CPT_SHAPESHIFT,
    CPT_UNISWAP,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

UNISWAP_DISTRIBUTOR = string_to_evm_address('0x090D4613473dEE047c3f2706764f49E0821D256e')
UNISWAP_TOKEN_CLAIMED = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501

BADGERHUNT = string_to_evm_address('0x394DCfbCf25C5400fcC147EbD9970eD34A474543')
BADGER_HUNT_EVENT = b'\x8e\xaf\x15aI\x08\xa4\xe9\x02!A\xfeJYk\x1a\xb0\xcbr\xab2\xb2P#\xe3\xda*E\x9c\x9a3\\'  # noqa: E501

ONEINCH = string_to_evm_address('0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe')
ONEINCH_CLAIMED = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501

FPIS = string_to_evm_address('0x61A1f84F12Ba9a56C22c31dDB10EC2e2CA0ceBCf')
CONVEX = string_to_evm_address('0x2E088A0A19dda628B4304301d1EA70b114e4AcCd')
FPIS_CONVEX_CLAIM = b'G\xce\xe9|\xb7\xac\xd7\x17\xb3\xc0\xaa\x145\xd0\x04\xcd[<\x8cW\xd7\r\xbc\xebNDX\xbb\xd6\x0e9\xd4'  # noqa: E501

FOX_DISTRIBUTOR = string_to_evm_address('0xe099e688D12DBc19ab46D128d1Db297575474a0d')
FOX_CLAIMED = b"R\x897\xb30\x08-\x89*\x98\xd4\xe4(\xab-\xcc\xa7\x84KQ\xd2'\xa1\xc0\xaeg\xf0\xb5&\x1a\xcb\xd9"  # noqa: E501

ELFI_LOCKING = string_to_evm_address('0x02Bd4A3b1b95b01F2Aa61655415A5d3EAAcaafdD')
ELFI_VOTE_CHANGE = b'3\x16\x1c\xf2\xda(\xd7G\xbe\x9d\xf16\xb6\xf3r\x93\x90)\x84\x94\x94rht1\x93\xc5=s\xd3\xc2\xe0'  # noqa: E501


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AirdropsDecoder(CowswapAirdropDecoder):

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
            vcow=A_VCOW,
        )
        self.uni = A_UNI.resolve_to_evm_token()
        self.fox = A_FOX.resolve_to_evm_token()
        self.badger = A_BADGER.resolve_to_evm_token()
        self.oneinch = A_1INCH.resolve_to_evm_token()
        self.convex = A_CVX.resolve_to_evm_token()
        self.fpis = A_FPIS.resolve_to_evm_token()
        self.elfi = A_ELFI.resolve_to_evm_token()

    def _decode_uniswap_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != UNISWAP_TOKEN_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        user_address = hex_or_bytes_to_address(context.tx_log.data[32:64])
        raw_amount = hex_or_bytes_to_int(context.tx_log.data[64:96])
        amount = asset_normalized_value(amount=raw_amount, asset=self.uni)
        for event in context.decoded_events:
            if match_airdrop_claim(
                event=event,
                user_address=user_address,
                amount=amount,
                asset=self.fox,
                counterparty=CPT_UNISWAP,
            ):
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_fox_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != FOX_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        raw_amount = hex_or_bytes_to_int(context.tx_log.data[64:96])
        amount = asset_normalized_value(amount=raw_amount, asset=self.fox)
        user_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        for event in context.decoded_events:
            if match_airdrop_claim(
                event=event,
                user_address=user_address,
                amount=amount,
                asset=self.fox,
                counterparty=CPT_SHAPESHIFT,
            ):
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_badger_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != BADGER_HUNT_EVENT:
            return DEFAULT_DECODING_OUTPUT

        raw_amount = hex_or_bytes_to_int(context.tx_log.data[32:64])
        amount = asset_normalized_value(amount=raw_amount, asset=self.badger)
        user_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        for event in context.decoded_events:
            if match_airdrop_claim(
                event=event,
                user_address=user_address,
                amount=amount,
                asset=self.badger,
                counterparty=CPT_BADGER,
            ):
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_oneinch_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != ONEINCH_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        raw_amount = hex_or_bytes_to_int(context.tx_log.data[64:96])
        amount = asset_normalized_value(amount=raw_amount, asset=self.oneinch)
        user_address = hex_or_bytes_to_address(context.tx_log.data[32:64])
        for event in context.decoded_events:
            if match_airdrop_claim(
                event=event,
                user_address=user_address,
                amount=amount,
                asset=self.oneinch,
                counterparty=CPT_ONEINCH,
            ):
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_fpis_claim(
            self,
            context: DecoderContext,
            airdrop: Literal['convex', 'fpis'],
    ) -> DecodingOutput:
        if context.tx_log.topics[0] != FPIS_CONVEX_CLAIM:
            return DEFAULT_DECODING_OUTPUT

        user_address = hex_or_bytes_to_address(context.tx_log.data[0:32])
        raw_amount = hex_or_bytes_to_int(context.tx_log.data[32:64])
        if airdrop == CPT_CONVEX:
            amount = asset_normalized_value(
                amount=raw_amount,
                asset=self.convex,
            )
            note_location = 'from convex airdrop'
            counterparty = CPT_CONVEX
        else:
            amount = asset_normalized_value(
                amount=raw_amount,
                asset=self.fpis,
            )
            note_location = 'from FPIS airdrop'
            counterparty = CPT_FRAX

        for event in context.decoded_events:
            notes = event.notes
            try:
                notes = f'Claim {amount} {event.asset.resolve_to_crypto_asset().symbol} {note_location}'  # noqa: E501
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=counterparty)

            if match_airdrop_claim(
                event=event,
                user_address=user_address,
                amount=amount,
                asset=self.fpis,
                counterparty=counterparty,
                notes=notes,
            ):
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_elfi_claim(self, context: DecoderContext) -> DecodingOutput:
        """Example:
        https://etherscan.io/tx/0x1e58aed1baf70b57e6e3e880e1890e7fe607fddc94d62986c38fe70e483e594b
        """
        if context.tx_log.topics[0] != ELFI_VOTE_CHANGE:
            return DEFAULT_DECODING_OUTPUT

        user_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        delegate_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        raw_amount = hex_or_bytes_to_int(context.tx_log.data[0:32])
        amount = asset_normalized_value(amount=raw_amount, asset=self.elfi)

        # now we need to find the transfer, but can't use decoded events
        # since the transfer is from one of at least 2 airdrop contracts to
        # vote/locking contract. Since neither the from, nor the to is a
        # tracked address there won't be a decoded transfer. So we search for
        # the raw log
        for other_log in context.all_logs:
            if other_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
                continue

            transfer_raw = hex_or_bytes_to_int(other_log.data[0:32])
            if (
                other_log.address == self.elfi.evm_address and
                transfer_raw == raw_amount
            ):
                delegate_str = 'self-delegate' if user_address == delegate_address else f'delegate it to {delegate_address}'  # noqa: E501
                event = self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.AIRDROP,
                    asset=self.elfi,
                    balance=Balance(amount=amount),
                    location_label=user_address,
                    notes=f'Claim {amount} ELFI from element-finance airdrop and {delegate_str}',
                    counterparty=CPT_ELEMENT_FINANCE,
                    address=context.transaction.to_address,
                )
                return DecodingOutput(event=event)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {
            UNISWAP_DISTRIBUTOR: (self._decode_uniswap_claim,),
            BADGERHUNT: (self._decode_badger_claim,),
            ONEINCH: (self._decode_oneinch_claim,),
            FPIS: (self._decode_fpis_claim, 'fpis'),
            CONVEX: (self._decode_fpis_claim, 'convex'),
            FOX_DISTRIBUTOR: (self._decode_fox_claim,),
            ELFI_LOCKING: (self._decode_elfi_claim,),
        } | super().addresses_to_decoders()

    def counterparties(self) -> list[CounterpartyDetails]:
        return [
            CounterpartyDetails(
                identifier=CPT_BADGER,
                label='Badger',
                image='badger.png',
            ),
            CounterpartyDetails(
                identifier=CPT_UNISWAP,
                label=UNISWAP_LABEL,
                image=UNISWAP_ICON,
            ),
            CounterpartyDetails(
                identifier=CPT_ONEINCH,
                label=ONEINCH_LABEL,
                image=ONEINCH_ICON,
            ),
            CONVEX_CPT_DETAILS,
            CounterpartyDetails(
                identifier=CPT_FRAX,
                label='FRAX',
                image='frax.png',
            ),
            CounterpartyDetails(
                identifier=CPT_SHAPESHIFT,
                label='Shapeshift',
                image='shapeshift.svg',
            ),
            CounterpartyDetails(
                identifier=CPT_ELEMENT_FINANCE,
                label='Element Finance',
                image='element_finance.png',
            ),
            COWSWAP_CPT_DETAILS,
        ]
