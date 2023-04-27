from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.types import EventCategory, EventCategoryDetails


FREE_PNL_EVENTS_LIMIT = 1000
FREE_REPORTS_LOOKUP_LIMIT = 20


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
        HistoryEventSubType.FEE: EventCategory.FEE,
        HistoryEventSubType.MEV_REWARD: EventCategory.MEV_REWARD,
        HistoryEventSubType.BLOCK_PRODUCTION: EventCategory.CREATE_BLOCK,
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
    EventCategory.FEE: EventCategoryDetails(
        label='fee',
        icon='mdi-account-cash',
    ),
    EventCategory.MEV_REWARD: EventCategoryDetails(
        label='mev',
        icon='mdi-star-box',
    ),
    EventCategory.CREATE_BLOCK: EventCategoryDetails(
        label='new block',
        icon='mdi-cube-outline',
    ),
}
