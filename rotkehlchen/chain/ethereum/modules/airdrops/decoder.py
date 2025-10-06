import logging
from typing import TYPE_CHECKING, Any, Final, Literal

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.convex.constants import CONVEX_CPT_DETAILS, CPT_CONVEX
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS, ENS_CPT_DETAILS
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, SIMPLE_CLAIM
from rotkehlchen.chain.evm.decoding.airdrops import match_airdrop_claim
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.cowswap.constants import COWSWAP_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import MerkleClaimDecoderInterface
from rotkehlchen.chain.evm.decoding.oneinch.constants import ONEINCH_ICON, ONEINCH_LABEL
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.constants import UNISWAP_ICON, UNISWAP_LABEL
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_BADGER,
    A_CVX,
    A_ELFI,
    A_ENS,
    A_FOX,
    A_FPIS,
    A_UNI,
)
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CPT_BADGER,
    CPT_ELEMENT_FINANCE,
    CPT_FRAX,
    CPT_ONEINCH,
    CPT_SHAPESHIFT,
    CPT_UNISWAP,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

UNISWAP_DISTRIBUTOR: Final = string_to_evm_address('0x090D4613473dEE047c3f2706764f49E0821D256e')

BADGERHUNT: Final = string_to_evm_address('0x394DCfbCf25C5400fcC147EbD9970eD34A474543')
BADGER_HUNT_EVENT: Final = b'\x8e\xaf\x15aI\x08\xa4\xe9\x02!A\xfeJYk\x1a\xb0\xcbr\xab2\xb2P#\xe3\xda*E\x9c\x9a3\\'  # noqa: E501

ONEINCH: Final = string_to_evm_address('0xE295aD71242373C37C5FdA7B57F26f9eA1088AFe')

FPIS: Final = string_to_evm_address('0x61A1f84F12Ba9a56C22c31dDB10EC2e2CA0ceBCf')
CONVEX: Final = string_to_evm_address('0x2E088A0A19dda628B4304301d1EA70b114e4AcCd')

FOX_DISTRIBUTORS: Final = (
    string_to_evm_address('0x91B9A78658273913bf3F5444Cb5F2592d1123eA7'),
    string_to_evm_address('0xB90381DAE1a72528660278100C5Aa44e1108ceF7'),
    string_to_evm_address('0x7BC08798465B8475Db9BCA781C2Fd6063A09320D'),
    string_to_evm_address('0xd28b7Ca9c6Bf8BB82Ea3d7F9948304F7C0B4e907'),
    string_to_evm_address('0xCd966F6F78100CB9e02724bb6A82081D078Cc37A'),
    string_to_evm_address('0xa6c22196309eF252232a0C62951fcEC1FE3b26FB'),
    string_to_evm_address('0xa4A3603000F5495F924A5C474AF67622B6b9c8Fa'),
    string_to_evm_address('0xf4BBE639CCEd35210dA2018b0A31f4E1449B2a8a'),
    string_to_evm_address('0x164D113F46676CA92d54537aC5aF10aC20940b94'),
    string_to_evm_address('0x02FfdC5bfAbe5c66BE067ff79231585082CA5fe2'),
    string_to_evm_address('0xd1Fa5AA6AD65eD6FEA863c2e7fB91e731DcD559F'),
    string_to_evm_address('0x01F89EB04481052A75D32D726Cc5b6B2f567001D'),
    string_to_evm_address('0x2977F92D5BaddfB411beb642F97d125aA55C000A'),
    string_to_evm_address('0xe099e688D12DBc19ab46D128d1Db297575474a0d'),
    string_to_evm_address('0x0DCDc346ADF5a808F8e683C31BA89fA6C6E5775D'),
    string_to_evm_address('0x4C20CDAdBcaE364Edc03E2B90F09eB97d08ce3C8'),
)
FOX_CLAIMED: Final = b"R\x897\xb30\x08-\x89*\x98\xd4\xe4(\xab-\xcc\xa7\x84KQ\xd2'\xa1\xc0\xaeg\xf0\xb5&\x1a\xcb\xd9"  # noqa: E501

ELFI_LOCKING: Final = string_to_evm_address('0x02Bd4A3b1b95b01F2Aa61655415A5d3EAAcaafdD')
ELFI_ADDRESS: Final = string_to_evm_address('0x5c6D51ecBA4D8E4F20373e3ce96a62342B125D6d')
ELFI_VOTE_CHANGE: Final = b'3\x16\x1c\xf2\xda(\xd7G\xbe\x9d\xf16\xb6\xf3r\x93\x90)\x84\x94\x94rht1\x93\xc5=s\xd3\xc2\xe0'  # noqa: E501
ENS_ADDRESS: Final = string_to_evm_address('0xC18360217D8F7Ab5e7c516566761Ea12Ce7F9D72')


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AirdropsDecoder(MerkleClaimDecoderInterface):

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

    def _decode_fox_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != FOX_CLAIMED:
            return DEFAULT_EVM_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[64:96])
        amount = token_normalized_value_decimals(
            token_amount=raw_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # fox 18 decimals
        )
        user_address = bytes_to_address(context.tx_log.topics[1])
        for event in context.decoded_events:
            if match_airdrop_claim(
                event=event,
                user_address=user_address,
                amount=amount,
                asset=A_FOX,
                counterparty=CPT_SHAPESHIFT,
                airdrop_identifier='shapeshift',
            ):
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_badger_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != BADGER_HUNT_EVENT:
            return DEFAULT_EVM_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[32:64])
        amount = token_normalized_value_decimals(
            token_amount=raw_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # badger 18 decimals
        )
        user_address = bytes_to_address(context.tx_log.topics[1])
        for event in context.decoded_events:
            if match_airdrop_claim(
                event=event,
                user_address=user_address,
                amount=amount,
                asset=A_BADGER,
                counterparty=CPT_BADGER,
                airdrop_identifier='badger',
            ):
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_fpis_claim(
            self,
            context: DecoderContext,
            airdrop: Literal['convex', 'fpis'],
    ) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != SIMPLE_CLAIM:
            return DEFAULT_EVM_DECODING_OUTPUT

        user_address = bytes_to_address(context.tx_log.data[0:32])
        raw_amount = int.from_bytes(context.tx_log.data[32:64])

        if airdrop == CPT_CONVEX:
            amount = token_normalized_value_decimals(
                token_amount=raw_amount,
                token_decimals=DEFAULT_TOKEN_DECIMALS,  # convex 18 decimals
            )
            note_location = 'from convex airdrop'
            counterparty = CPT_CONVEX
            airdrop_asset = A_CVX
        else:
            amount = token_normalized_value_decimals(
                token_amount=raw_amount,
                token_decimals=DEFAULT_TOKEN_DECIMALS,  # fpis 18 decimals
            )
            note_location = 'from FPIS airdrop'
            counterparty = CPT_FRAX
            airdrop_asset = A_FPIS

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
                asset=airdrop_asset,
                counterparty=counterparty,
                notes=notes,
                airdrop_identifier=airdrop,
            ):
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_elfi_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        """Example:
        https://etherscan.io/tx/0x1e58aed1baf70b57e6e3e880e1890e7fe607fddc94d62986c38fe70e483e594b
        """
        if context.tx_log.topics[0] != ELFI_VOTE_CHANGE:
            return DEFAULT_EVM_DECODING_OUTPUT

        user_address = bytes_to_address(context.tx_log.topics[1])
        delegate_address = bytes_to_address(context.tx_log.topics[2])
        raw_amount = int.from_bytes(context.tx_log.data[0:32])
        amount = token_normalized_value_decimals(
            token_amount=raw_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # elfi 18 decimals
        )

        # now we need to find the transfer, but can't use decoded events
        # since the transfer is from one of at least 2 airdrop contracts to
        # vote/locking contract. Since neither the from, nor the to is a
        # tracked address there won't be a decoded transfer. So we search for
        # the raw log
        for other_log in context.all_logs:
            if other_log.topics[0] != ERC20_OR_ERC721_TRANSFER:
                continue

            transfer_raw = int.from_bytes(other_log.data[0:32])
            if (
                other_log.address == ELFI_ADDRESS and
                transfer_raw == raw_amount
            ):
                delegate_str = 'self-delegate' if user_address == delegate_address else f'delegate it to {delegate_address}'  # noqa: E501
                event = self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.AIRDROP,
                    asset=A_ELFI,
                    amount=amount,
                    location_label=user_address,
                    notes=f'Claim {amount} ELFI from element-finance airdrop and {delegate_str}',
                    counterparty=CPT_ELEMENT_FINANCE,
                    address=context.transaction.to_address,
                    extra_data={AIRDROP_IDENTIFIER_KEY: 'elfi'},
                )
                return EvmDecodingOutput(events=[event])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_ens_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != SIMPLE_CLAIM:
            return DEFAULT_EVM_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[:32])
        amount = token_normalized_value_decimals(
            token_amount=raw_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # ens 18 decimals
        )
        user_address = bytes_to_address(context.tx_log.topics[1])
        return EvmDecodingOutput(
            action_items=[
                ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.RECEIVE,
                    from_event_subtype=HistoryEventSubType.NONE,
                    location_label=user_address,
                    asset=A_ENS,
                    amount=amount,
                    to_event_subtype=HistoryEventSubType.AIRDROP,
                    to_counterparty=CPT_ENS,
                    to_notes=f'Claim {amount} ENS from {CPT_ENS} airdrop',
                    extra_data={AIRDROP_IDENTIFIER_KEY: 'ens'},
                ),
            ],
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {
            UNISWAP_DISTRIBUTOR: (
                self._decode_merkle_claim,
                CPT_UNISWAP,  # counterparty
                A_UNI.identifier,  # token id
                18,  # token decimals
                'UNI from the uniswap airdrop',  # notes suffix
                'uniswap',
            ),
            BADGERHUNT: (self._decode_badger_claim,),
            ONEINCH: (
                self._decode_merkle_claim,
                CPT_ONEINCH,  # counterparty
                A_1INCH.identifier,  # token id
                18,  # token decimals
                '1inch from the 1inch airdrop',  # notes suffix
                '1inch',
            ),
            FPIS: (self._decode_fpis_claim, 'fpis'),
            CONVEX: (self._decode_fpis_claim, 'convex'),
            ELFI_LOCKING: (self._decode_elfi_claim,),
            ENS_ADDRESS: (self._decode_ens_claim,),
        } | dict.fromkeys(FOX_DISTRIBUTORS, (self._decode_fox_claim,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
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
            COWSWAP_CPT_DETAILS,  # done by cowswap decoder. Stays here since we query airdrop counterparties in some places ... perhaps rethink this. It's not a good abstraction  # noqa: E501
            ENS_CPT_DETAILS,
        )
