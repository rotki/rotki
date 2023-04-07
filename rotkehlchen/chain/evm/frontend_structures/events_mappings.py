from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.frontend_structures.types import EventDetails, TransactionEventType


DEFAULT_FRONTEND_MAPPINGS = {
    HistoryEventType.SPEND: {
        HistoryEventSubType.FEE: TransactionEventType.GAS,
        HistoryEventSubType.PAYBACK_DEBT: TransactionEventType.REPAY,
        HistoryEventSubType.RETURN_WRAPPED: TransactionEventType.SEND,
        HistoryEventSubType.LIQUIDATE: TransactionEventType.LIQUIDATE,
        HistoryEventSubType.NONE: TransactionEventType.SEND,
    },
    HistoryEventType.RECEIVE: {
        HistoryEventSubType.GENERATE_DEBT: TransactionEventType.BORROW,
        HistoryEventSubType.RECEIVE_WRAPPED: TransactionEventType.RECEIVE,
        HistoryEventSubType.RETURN_WRAPPED: TransactionEventType.RECEIVE,
        HistoryEventSubType.AIRDROP: TransactionEventType.AIRDROP,
        HistoryEventSubType.REWARD: TransactionEventType.CLAIM_REWARD,
        HistoryEventSubType.NONE: TransactionEventType.RECEIVE,
        HistoryEventSubType.NFT: TransactionEventType.RECEIVE,
    },
    HistoryEventType.INFORMATIONAL: {
        HistoryEventSubType.APPROVE: TransactionEventType.APPROVAL,
        HistoryEventSubType.GOVERNANCE: TransactionEventType.GOVERNANCE,
        HistoryEventSubType.DEPLOY: TransactionEventType.DEPLOY,
        HistoryEventSubType.REMOVE_ASSET: TransactionEventType.WITHDRAW,
        HistoryEventSubType.PLACE_ORDER: TransactionEventType.PLACE_ORDER,
        HistoryEventSubType.NONE: TransactionEventType.INFORMATIONAL,
    },
    HistoryEventType.TRANSFER: {
        HistoryEventSubType.NONE: TransactionEventType.TRANSFER,
        HistoryEventSubType.BRIDGE: TransactionEventType.BRIDGE,
    },
    HistoryEventType.TRADE: {
        HistoryEventSubType.SPEND: TransactionEventType.SWAP_OUT,
        HistoryEventSubType.RECEIVE: TransactionEventType.SWAP_IN,
    },
    HistoryEventType.WITHDRAWAL: {
        HistoryEventSubType.NONE: TransactionEventType.WITHDRAW,
        HistoryEventSubType.REMOVE_ASSET: TransactionEventType.WITHDRAW,
        HistoryEventSubType.GENERATE_DEBT: TransactionEventType.BORROW,
        HistoryEventSubType.BRIDGE: TransactionEventType.BRIDGE,
    },
    HistoryEventType.DEPOSIT: {
        HistoryEventSubType.NONE: TransactionEventType.DEPOSIT,
        HistoryEventSubType.DEPOSIT_ASSET: TransactionEventType.DEPOSIT,
        HistoryEventSubType.BRIDGE: TransactionEventType.BRIDGE,
        HistoryEventSubType.PLACE_ORDER: TransactionEventType.PLACE_ORDER,
    },
    HistoryEventType.MIGRATE: {
        HistoryEventSubType.SPEND: TransactionEventType.SEND,
        HistoryEventSubType.RECEIVE: TransactionEventType.RECEIVE,
    },
    HistoryEventType.STAKING: {
        HistoryEventSubType.DEPOSIT_ASSET: TransactionEventType.DEPOSIT,
        HistoryEventSubType.REWARD: TransactionEventType.RECEIVE,
        HistoryEventSubType.RECEIVE_WRAPPED: TransactionEventType.RECEIVE,
        HistoryEventSubType.REMOVE_ASSET: TransactionEventType.WITHDRAW,
        HistoryEventSubType.RETURN_WRAPPED: TransactionEventType.SEND,
    },
}


EVENT_DETAILS = {
    TransactionEventType.GAS: EventDetails(
        label='gas fee',
        icon='mdi-fire',
    ),
    TransactionEventType.SEND: EventDetails(
        label='send',
        icon='mdi-arrow-up',
    ),
    TransactionEventType.RECEIVE: EventDetails(
        label='receive',
        icon='mdi-arrow-down',
        color='green',
    ),
    TransactionEventType.SWAP_OUT: EventDetails(
        label='swap out',
        icon='mdi-arrow-u-right-bottom',
    ),
    TransactionEventType.SWAP_IN: EventDetails(
        label='swap in',
        icon='mdi-arrow-u-left-top',
        color='green',
    ),
    TransactionEventType.APPROVAL: EventDetails(
        label='approval',
        icon='mdi-lock-open-outline',
    ),
    TransactionEventType.DEPOSIT: EventDetails(
        label='deposit',
        icon='mdi-arrow-expand-up',
        color='green',
    ),
    TransactionEventType.WITHDRAW: EventDetails(
        label='withdraw',
        icon='mdi-arrow-expand-down',
    ),
    TransactionEventType.AIRDROP: EventDetails(
        label='airdrop',
        icon='mdi-airballoon-outline',
    ),
    TransactionEventType.BORROW: EventDetails(
        label='borrow',
        icon='mdi-hand-coin-outline',
    ),
    TransactionEventType.REPAY: EventDetails(
        label='repay',
        icon='mdi-history',
    ),
    TransactionEventType.DEPLOY: EventDetails(
        label='deploy',
        icon='mdi-swap-horizontal',
    ),
    TransactionEventType.BRIDGE: EventDetails(
        label='bridge',
        icon='mdi-bridge',
    ),
    TransactionEventType.GOVERNANCE: EventDetails(
        label='governance',
        icon='mdi-bank',
    ),
    TransactionEventType.DONATE: EventDetails(
        label='donate',
        icon='mdi-hand-heart-outline',
    ),
    TransactionEventType.RECEIVE_DONATION: EventDetails(
        label='receive donation',
        icon='mdi-hand-heart-outline',
    ),
    TransactionEventType.RENEW: EventDetails(
        label='renew',
        icon='mdi-calendar-refresh',
    ),
    TransactionEventType.PLACE_ORDER: EventDetails(
        label='place order',
        icon='mdi-briefcase-arrow-up-down',
    ),
    TransactionEventType.TRANSFER: EventDetails(
        label='transfer',
        icon='mdi-swap-horizontal',
    ),
    TransactionEventType.CLAIM_REWARD: EventDetails(
        label='claim reward',
        icon='mdi-gift',
    ),
    TransactionEventType.LIQUIDATE: EventDetails(
        label='liquidate',
        icon='mdi-water',
    ),
    TransactionEventType.INFORMATIONAL: EventDetails(
        label='informational',
        icon='mdi-information-outline',
    ),
    TransactionEventType.CANCEL_ORDER: EventDetails(
        label='cancel order',
        icon='mdi-close-circle-multiple-outline',
        color='red',
    ),
    TransactionEventType.REFUND: EventDetails(
        label='refund',
        icon='mdi-cash-refund',
    ),
}
