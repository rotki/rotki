from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.types import (
    CounterpartyDetails,
    EventCategory,
    EventCategoryDetails,
)
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM

CPT_GAS = 'gas'
CPT_HOP = 'hop-protocol'

OUTGOING_EVENT_TYPES = {
    HistoryEventType.SPEND,
    HistoryEventType.TRANSFER,
    HistoryEventType.DEPOSIT,
}

# keccak of Transfer(address,address,uint256)
ERC20_OR_ERC721_TRANSFER = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501
# keccak of approve(address,uint256)
ERC20_APPROVE = b'\x8c[\xe1\xe5\xeb\xec}[\xd1OqB}\x1e\x84\xf3\xdd\x03\x14\xc0\xf7\xb2)\x1e[ \n\xc8\xc7\xc3\xb9%'  # noqa: E501

# Counterparty details shared between chains
HOP_DETAILS = CounterpartyDetails(
    identifier=CPT_HOP,
    label='Hop Protocol',
    image='hop_protocol.png',
)
OPTIMISM_DETAILS = CounterpartyDetails(
    identifier=CPT_OPTIMISM,
    label='Optimism',
    image='optimism.svg',
)

DEFAULT_EVENT_CATEGORY_MAPPINGS = {
    HistoryEventType.SPEND: {
        HistoryEventSubType.FEE: EventCategory.GAS,
        HistoryEventSubType.PAYBACK_DEBT: EventCategory.REPAY,
        HistoryEventSubType.RETURN_WRAPPED: EventCategory.SEND,
        HistoryEventSubType.LIQUIDATE: EventCategory.LIQUIDATE,
        HistoryEventSubType.NONE: EventCategory.SEND,
    },
    HistoryEventType.RECEIVE: {
        HistoryEventSubType.GENERATE_DEBT: EventCategory.BORROW,
        HistoryEventSubType.RECEIVE_WRAPPED: EventCategory.RECEIVE,
        HistoryEventSubType.RETURN_WRAPPED: EventCategory.RECEIVE,
        HistoryEventSubType.AIRDROP: EventCategory.AIRDROP,
        HistoryEventSubType.REWARD: EventCategory.CLAIM_REWARD,
        HistoryEventSubType.NONE: EventCategory.RECEIVE,
        HistoryEventSubType.NFT: EventCategory.RECEIVE,
    },
    HistoryEventType.INFORMATIONAL: {
        HistoryEventSubType.APPROVE: EventCategory.APPROVAL,
        HistoryEventSubType.GOVERNANCE: EventCategory.GOVERNANCE,
        HistoryEventSubType.DEPLOY: EventCategory.DEPLOY,
        HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
        HistoryEventSubType.PLACE_ORDER: EventCategory.PLACE_ORDER,
        HistoryEventSubType.NONE: EventCategory.INFORMATIONAL,
    },
    HistoryEventType.TRANSFER: {
        HistoryEventSubType.NONE: EventCategory.TRANSFER,
        HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
    },
    HistoryEventType.TRADE: {
        HistoryEventSubType.SPEND: EventCategory.SWAP_OUT,
        HistoryEventSubType.RECEIVE: EventCategory.SWAP_IN,
    },
    HistoryEventType.WITHDRAWAL: {
        HistoryEventSubType.NONE: EventCategory.WITHDRAW,
        HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
        HistoryEventSubType.GENERATE_DEBT: EventCategory.BORROW,
        HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
    },
    HistoryEventType.DEPOSIT: {
        HistoryEventSubType.NONE: EventCategory.DEPOSIT,
        HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
        HistoryEventSubType.BRIDGE: EventCategory.BRIDGE,
        HistoryEventSubType.PLACE_ORDER: EventCategory.PLACE_ORDER,
    },
    HistoryEventType.MIGRATE: {
        HistoryEventSubType.SPEND: EventCategory.SEND,
        HistoryEventSubType.RECEIVE: EventCategory.RECEIVE,
    },
    HistoryEventType.STAKING: {
        HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
        HistoryEventSubType.REWARD: EventCategory.RECEIVE,
        HistoryEventSubType.RECEIVE_WRAPPED: EventCategory.RECEIVE,
        HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
        HistoryEventSubType.RETURN_WRAPPED: EventCategory.SEND,
    },
}

EVENT_CATEGORY_DETAILS = {
    EventCategory.GAS: EventCategoryDetails(
        label='gas fee',
        icon='mdi-fire',
    ),
    EventCategory.SEND: EventCategoryDetails(
        label='send',
        icon='mdi-arrow-up',
    ),
    EventCategory.RECEIVE: EventCategoryDetails(
        label='receive',
        icon='mdi-arrow-down',
        color='green',
    ),
    EventCategory.SWAP_OUT: EventCategoryDetails(
        label='swap out',
        icon='mdi-arrow-u-right-bottom',
    ),
    EventCategory.SWAP_IN: EventCategoryDetails(
        label='swap in',
        icon='mdi-arrow-u-left-top',
        color='green',
    ),
    EventCategory.APPROVAL: EventCategoryDetails(
        label='approval',
        icon='mdi-lock-open-outline',
    ),
    EventCategory.DEPOSIT: EventCategoryDetails(
        label='deposit',
        icon='mdi-arrow-expand-up',
        color='green',
    ),
    EventCategory.WITHDRAW: EventCategoryDetails(
        label='withdraw',
        icon='mdi-arrow-expand-down',
    ),
    EventCategory.AIRDROP: EventCategoryDetails(
        label='airdrop',
        icon='mdi-airballoon-outline',
    ),
    EventCategory.BORROW: EventCategoryDetails(
        label='borrow',
        icon='mdi-hand-coin-outline',
    ),
    EventCategory.REPAY: EventCategoryDetails(
        label='repay',
        icon='mdi-history',
    ),
    EventCategory.DEPLOY: EventCategoryDetails(
        label='deploy',
        icon='mdi-swap-horizontal',
    ),
    EventCategory.BRIDGE: EventCategoryDetails(
        label='bridge',
        icon='mdi-bridge',
    ),
    EventCategory.GOVERNANCE: EventCategoryDetails(
        label='governance',
        icon='mdi-bank',
    ),
    EventCategory.DONATE: EventCategoryDetails(
        label='donate',
        icon='mdi-hand-heart-outline',
    ),
    EventCategory.RECEIVE_DONATION: EventCategoryDetails(
        label='receive donation',
        icon='mdi-hand-heart-outline',
    ),
    EventCategory.RENEW: EventCategoryDetails(
        label='renew',
        icon='mdi-calendar-refresh',
    ),
    EventCategory.PLACE_ORDER: EventCategoryDetails(
        label='place order',
        icon='mdi-briefcase-arrow-up-down',
    ),
    EventCategory.TRANSFER: EventCategoryDetails(
        label='transfer',
        icon='mdi-swap-horizontal',
    ),
    EventCategory.CLAIM_REWARD: EventCategoryDetails(
        label='claim reward',
        icon='mdi-gift',
    ),
    EventCategory.LIQUIDATE: EventCategoryDetails(
        label='liquidate',
        icon='mdi-water',
    ),
    EventCategory.INFORMATIONAL: EventCategoryDetails(
        label='informational',
        icon='mdi-information-outline',
    ),
    EventCategory.CANCEL_ORDER: EventCategoryDetails(
        label='cancel order',
        icon='mdi-close-circle-multiple-outline',
        color='red',
    ),
    EventCategory.REFUND: EventCategoryDetails(
        label='refund',
        icon='mdi-cash-refund',
    ),
}
