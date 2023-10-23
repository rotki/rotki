from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.types import (
    EventCategory,
    EventCategoryDetails,
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)

FREE_PNL_EVENTS_LIMIT = 1000
FREE_REPORTS_LOOKUP_LIMIT = 20

EVENT_CATEGORY_MAPPINGS = {  # possible combinations of types and subtypes mapped to their event category  # noqa: E501
    HistoryEventType.INFORMATIONAL: {
        HistoryEventSubType.NONE: EventCategory.INFORMATIONAL,
        HistoryEventSubType.GOVERNANCE: EventCategory.GOVERNANCE,
        HistoryEventSubType.REMOVE_ASSET: EventCategory.INFORMATIONAL,
        HistoryEventSubType.PLACE_ORDER: EventCategory.PLACE_ORDER,
        HistoryEventSubType.CREATE: EventCategory.CREATE_PROJECT,
        HistoryEventSubType.UPDATE: EventCategory.UPDATE_PROJECT,
        HistoryEventSubType.APPLY: EventCategory.APPLY,
        HistoryEventSubType.APPROVE: EventCategory.APPROVAL,
    }, HistoryEventType.RECEIVE: {
        HistoryEventSubType.REWARD: EventCategory.CLAIM_REWARD,
        HistoryEventSubType.RECEIVE_WRAPPED: EventCategory.RECEIVE,
        HistoryEventSubType.GENERATE_DEBT: EventCategory.BORROW,
        HistoryEventSubType.RETURN_WRAPPED: EventCategory.RECEIVE,
        HistoryEventSubType.AIRDROP: EventCategory.AIRDROP,
        HistoryEventSubType.DONATE: EventCategory.RECEIVE_DONATION,
        HistoryEventSubType.NONE: EventCategory.RECEIVE,
        HistoryEventSubType.LIQUIDATE: EventCategory.LIQUIDATION_REWARD,
    }, HistoryEventType.DEPOSIT: {
        HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
        HistoryEventSubType.BRIDGE: EventCategory.BRIDGE_DEPOSIT,
        HistoryEventSubType.PLACE_ORDER: EventCategory.DEPOSIT,
        HistoryEventSubType.FEE: EventCategory.FEE,
    }, HistoryEventType.SPEND: {
        HistoryEventSubType.RETURN_WRAPPED: EventCategory.SEND,
        HistoryEventSubType.LIQUIDATE: EventCategory.LIQUIDATION_LOSS,
        HistoryEventSubType.PAYBACK_DEBT: EventCategory.REPAY,
        HistoryEventSubType.FEE: EventCategory.FEE,
        HistoryEventSubType.DONATE: EventCategory.DONATE,
        HistoryEventSubType.NONE: EventCategory.SEND,
    }, HistoryEventType.WITHDRAWAL: {
        HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
        HistoryEventSubType.BRIDGE: EventCategory.BRIDGE_WITHDRAWAL,
        HistoryEventSubType.CANCEL_ORDER: EventCategory.CANCEL_ORDER,
        HistoryEventSubType.REFUND: EventCategory.REFUND,
        HistoryEventSubType.GENERATE_DEBT: EventCategory.BORROW,
        HistoryEventSubType.FEE: EventCategory.FEE,
    }, HistoryEventType.TRADE: {
        HistoryEventSubType.SPEND: EventCategory.SWAP_OUT,
        HistoryEventSubType.RECEIVE: EventCategory.SWAP_IN,
        HistoryEventSubType.NONE: EventCategory.INFORMATIONAL,  # verify
        HistoryEventSubType.FEE: EventCategory.FEE,
    }, HistoryEventType.RENEW: {
        HistoryEventSubType.NFT: EventCategory.RENEW,
    }, HistoryEventType.STAKING: {
        HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
        HistoryEventSubType.REWARD: EventCategory.STAKING_REWARD,
        HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
        HistoryEventSubType.BLOCK_PRODUCTION: EventCategory.CREATE_BLOCK,
        HistoryEventSubType.MEV_REWARD: EventCategory.MEV_REWARD,
        HistoryEventSubType.RECEIVE_WRAPPED: EventCategory.RECEIVE,
    }, HistoryEventType.TRANSFER: {
        HistoryEventSubType.DONATE: EventCategory.DONATE,
        HistoryEventSubType.NONE: EventCategory.TRANSFER,
    }, HistoryEventType.ADJUSTMENT: {
        HistoryEventSubType.SPEND: EventCategory.SEND,
        HistoryEventSubType.RECEIVE: EventCategory.RECEIVE,
    }, HistoryEventType.DEPLOY: {
        HistoryEventSubType.NONE: EventCategory.DEPLOY,
        HistoryEventSubType.SPEND: EventCategory.DEPLOY_WITH_SPEND,
        HistoryEventSubType.NFT: EventCategory.DEPLOY,
    }, HistoryEventType.MIGRATE: {
        HistoryEventSubType.SPEND: EventCategory.MIGRATE_OUT,
        HistoryEventSubType.RECEIVE: EventCategory.MIGRATE_IN,
    },
}

EVENT_CATEGORY_DETAILS = {
    EventCategory.GAS: EventCategoryDetails(
        label='gas fee',
        icon='mdi-fire',
        direction=EventDirection.OUT,
    ), EventCategory.SEND: EventCategoryDetails(
        label='send',
        icon='mdi-arrow-up',
        direction=EventDirection.OUT,
    ), EventCategory.RECEIVE: EventCategoryDetails(
        label='receive',
        icon='mdi-arrow-down',
        color='green',
        direction=EventDirection.IN,
    ), EventCategory.SWAP_OUT: EventCategoryDetails(
        label='swap',
        icon='mdi-arrow-u-right-bottom',
        direction=EventDirection.OUT,
    ), EventCategory.SWAP_IN: EventCategoryDetails(
        label='swap',
        icon='mdi-arrow-u-left-top',
        color='green',
        direction=EventDirection.IN,
    ), EventCategory.MIGRATE_OUT: EventCategoryDetails(
        label='migrate',
        icon='mdi-arrow-u-right-bottom',
        direction=EventDirection.OUT,
    ), EventCategory.MIGRATE_IN: EventCategoryDetails(
        label='migrate',
        icon='mdi-arrow-u-left-top',
        color='green',
        direction=EventDirection.IN,
    ), EventCategory.APPROVAL: EventCategoryDetails(
        label='approval',
        icon='mdi-lock-open-outline',
        direction=EventDirection.NEUTRAL,
    ), EventCategory.DEPOSIT: EventCategoryDetails(
        label='deposit',
        icon='mdi-arrow-expand-up',
        color='green',
        direction=EventDirection.OUT,
    ), EventCategory.WITHDRAW: EventCategoryDetails(
        label='withdraw',
        icon='mdi-arrow-expand-down',
        direction=EventDirection.IN,
    ), EventCategory.AIRDROP: EventCategoryDetails(
        label='airdrop',
        icon='mdi-airballoon-outline',
        direction=EventDirection.IN,
    ), EventCategory.BORROW: EventCategoryDetails(
        label='borrow',
        icon='mdi-hand-coin-outline',
        direction=EventDirection.IN,
    ), EventCategory.REPAY: EventCategoryDetails(
        label='repay',
        icon='mdi-history',
        direction=EventDirection.OUT,
    ), EventCategory.DEPLOY: EventCategoryDetails(
        label='deploy',
        icon='mdi-swap-horizontal',
        direction=EventDirection.NEUTRAL,
    ), EventCategory.DEPLOY_WITH_SPEND: EventCategoryDetails(
        label='deploy with spend',
        icon='mdi-swap-horizontal',
        direction=EventDirection.OUT,
    ), EventCategory.BRIDGE_DEPOSIT: EventCategoryDetails(
        label='bridge',
        icon='mdi-arrow-expand-up',
        color='red',
        direction=EventDirection.OUT,
    ), EventCategory.BRIDGE_WITHDRAWAL: EventCategoryDetails(
        label='bridge',
        icon='mdi-arrow-expand-down',
        color='green',
        direction=EventDirection.IN,
    ), EventCategory.GOVERNANCE: EventCategoryDetails(
        label='governance',
        icon='mdi-bank',
        direction=EventDirection.NEUTRAL,
    ), EventCategory.DONATE: EventCategoryDetails(
        label='donate',
        icon='mdi-hand-heart-outline',
        direction=EventDirection.OUT,
    ), EventCategory.RECEIVE_DONATION: EventCategoryDetails(
        label='receive donation',
        icon='mdi-hand-heart-outline',
        direction=EventDirection.IN,
    ), EventCategory.RENEW: EventCategoryDetails(
        label='renew',
        icon='mdi-calendar-refresh',
        direction=EventDirection.OUT,
    ), EventCategory.PLACE_ORDER: EventCategoryDetails(
        label='place order',
        icon='mdi-briefcase-arrow-up-down',
        direction=EventDirection.NEUTRAL,
    ), EventCategory.TRANSFER: EventCategoryDetails(
        label='transfer',
        icon='mdi-swap-horizontal',
        direction=EventDirection.NEUTRAL,
    ), EventCategory.STAKING_REWARD: EventCategoryDetails(
        label='staking reward',
        icon='mdi-treasure-chest',
        direction=EventDirection.IN,
    ), EventCategory.CLAIM_REWARD: EventCategoryDetails(
        label='claim reward',
        icon='mdi-gift',
        direction=EventDirection.IN,
    ), EventCategory.LIQUIDATION_REWARD: EventCategoryDetails(
        label='liquidation reward',
        icon='mdi-water',
        direction=EventDirection.IN,
    ), EventCategory.LIQUIDATION_LOSS: EventCategoryDetails(
        label='liquidation loss',
        icon='mdi-water',
        direction=EventDirection.OUT,
    ), EventCategory.INFORMATIONAL: EventCategoryDetails(
        label='informational',
        icon='mdi-information-outline',
        direction=EventDirection.NEUTRAL,
    ), EventCategory.CANCEL_ORDER: EventCategoryDetails(
        label='cancel order',
        icon='mdi-close-circle-multiple-outline',
        color='red',
        direction=EventDirection.IN,
    ), EventCategory.REFUND: EventCategoryDetails(
        label='refund',
        icon='mdi-cash-refund',
        direction=EventDirection.IN,
    ), EventCategory.FEE: EventCategoryDetails(
        label='fee',
        icon='mdi-account-cash',
        direction=EventDirection.OUT,
    ), EventCategory.MEV_REWARD: EventCategoryDetails(
        label='mev',
        icon='mdi-star-box',
        direction=EventDirection.IN,
    ), EventCategory.CREATE_BLOCK: EventCategoryDetails(
        label='new block',
        icon='mdi-cube-outline',
        direction=EventDirection.IN,
    ), EventCategory.CREATE_PROJECT: EventCategoryDetails(
        label='new project',
        icon='mdi-clipboard-check-outline',
        direction=EventDirection.NEUTRAL,
    ), EventCategory.UPDATE_PROJECT: EventCategoryDetails(
        label='update project',
        icon='mdi-clipboard-plus-outline',
        direction=EventDirection.NEUTRAL,
    ), EventCategory.APPLY: EventCategoryDetails(
        label='apply',
        icon='mdi-application-export',
        direction=EventDirection.NEUTRAL,
    ),
}

ACCOUNTING_EVENTS_ICONS = {
    AccountingEventType.TRADE: 'mdi-shuffle-variant',
    AccountingEventType.FEE: 'mdi-fire',
    AccountingEventType.ASSET_MOVEMENT: 'mdi-bank-transfer',
    AccountingEventType.MARGIN_POSITION: 'mdi-margin',
    AccountingEventType.LOAN: 'mdi-handshake',
    AccountingEventType.PREFORK_ACQUISITION: 'mdi-source-fork',
    AccountingEventType.STAKING: 'mdi-sprout',
    AccountingEventType.HISTORY_EVENT: 'mdi-history',
    AccountingEventType.TRANSACTION_EVENT: 'mdi-swap-horizontal',
}
