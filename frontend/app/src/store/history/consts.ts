import i18n from '@/i18n';
import { LedgerActionType } from '@/types/ledger-actions';
import {
  HistoryEventSubType,
  HistoryEventType,
  TransactionEventProtocol,
  TransactionEventType
} from '@/types/transaction';

export type ActionDataEntry = {
  readonly identifier: string;
  readonly label: string;
  readonly icon?: string | undefined;
  readonly image?: string | undefined;
  readonly color?: string | undefined;
  readonly matcher?: (identifier: string) => boolean | undefined;
};

export const ledgerActionsData: ActionDataEntry[] = [
  {
    identifier: LedgerActionType.ACTION_INCOME,
    label: i18n.t('ledger_actions.actions.income').toString()
  },
  {
    identifier: LedgerActionType.ACTION_LOSS,
    label: i18n.t('ledger_actions.actions.loss').toString()
  },
  {
    identifier: LedgerActionType.ACTION_DONATION,
    label: i18n.t('ledger_actions.actions.donation').toString()
  },
  {
    identifier: LedgerActionType.ACTION_EXPENSE,
    label: i18n.t('ledger_actions.actions.expense').toString()
  },
  {
    identifier: LedgerActionType.ACTION_DIVIDENDS,
    label: i18n.t('ledger_actions.actions.dividends').toString()
  },
  {
    identifier: LedgerActionType.ACTION_AIRDROP,
    label: i18n.t('ledger_actions.actions.airdrop').toString()
  },
  {
    identifier: LedgerActionType.ACTION_GIFT,
    label: i18n.t('ledger_actions.actions.gift').toString()
  },
  {
    identifier: LedgerActionType.ACTION_GRANT,
    label: i18n.t('ledger_actions.actions.grant').toString()
  }
];

export const transactionEventTypeData: ActionDataEntry[] = [
  {
    identifier: TransactionEventType.GAS,
    label: i18n.t('transactions.event_type.gas_fee').toString(),
    icon: 'mdi-fire'
  },
  {
    identifier: TransactionEventType.SEND,
    label: i18n.t('transactions.event_type.send').toString(),
    icon: 'mdi-arrow-up'
  },
  {
    identifier: TransactionEventType.RECEIVE,
    label: i18n.t('transactions.event_type.receive').toString(),
    icon: 'mdi-arrow-down',
    color: 'green'
  },
  {
    identifier: TransactionEventType.APPROVAL,
    label: i18n.t('transactions.event_type.approval').toString(),
    icon: 'mdi-lock-open-outline'
  },
  {
    identifier: TransactionEventType.DEPOSIT,
    label: i18n.t('transactions.event_type.deposit').toString(),
    icon: 'mdi-arrow-expand-up',
    color: 'green'
  },
  {
    identifier: TransactionEventType.WITHDRAW,
    label: i18n.t('transactions.event_type.withdraw').toString(),
    icon: 'mdi-arrow-expand-down'
  },
  {
    identifier: TransactionEventType.AIRDROP,
    label: i18n.t('transactions.event_type.airdrop').toString(),
    icon: 'mdi-airballoon-outline'
  },
  {
    identifier: TransactionEventType.BORROW,
    label: i18n.t('transactions.event_type.borrow').toString(),
    icon: 'mdi-hand-coin-outline'
  },
  {
    identifier: TransactionEventType.REPAY,
    label: i18n.t('transactions.event_type.repay').toString(),
    icon: 'mdi-history'
  },
  {
    identifier: TransactionEventType.DEPLOY,
    label: i18n.t('transactions.event_type.deploy').toString(),
    icon: 'mdi-swap-horizontal'
  },
  {
    identifier: TransactionEventType.BRIDGE,
    label: i18n.t('transactions.event_type.bridge').toString(),
    icon: 'mdi-bridge'
  },
  {
    identifier: TransactionEventType.GOVERNANCE_PROPOSE,
    label: i18n.t('transactions.event_type.governance_propose').toString(),
    icon: 'mdi-bank'
  }
];

export const transactionEventTypeMapping: {
  [type: string]: { [subType: string]: TransactionEventType };
} = {
  [HistoryEventType.SPEND]: {
    [HistoryEventSubType.FEE]: TransactionEventType.GAS,
    [HistoryEventSubType.PAYBACK_DEBT]: TransactionEventType.REPAY,
    [HistoryEventSubType.RETURN_WRAPPED]: TransactionEventType.SEND,
    null: TransactionEventType.SEND
  },
  [HistoryEventType.RECEIVE]: {
    [HistoryEventSubType.GENERATE_DEBT]: TransactionEventType.BORROW,
    [HistoryEventSubType.RECEIVE_WRAPPED]: TransactionEventType.RECEIVE,
    [HistoryEventSubType.RETURN_WRAPPED]: TransactionEventType.RECEIVE,
    [HistoryEventSubType.AIRDROP]: TransactionEventType.AIRDROP,
    null: TransactionEventType.RECEIVE
  },
  [HistoryEventType.INFORMATIONAL]: {
    [HistoryEventSubType.APPROVE]: TransactionEventType.APPROVAL,
    [HistoryEventSubType.GOVERNANCE_PROPOSE]:
      TransactionEventType.GOVERNANCE_PROPOSE,
    [HistoryEventSubType.DEPLOY]: TransactionEventType.DEPLOY
  },
  [HistoryEventType.TRANSFER]: {
    [HistoryEventSubType.BRIDGE]: TransactionEventType.BRIDGE
  },
  [HistoryEventType.TRADE]: {
    [HistoryEventSubType.SPEND]: TransactionEventType.SEND,
    [HistoryEventSubType.RECEIVE]: TransactionEventType.RECEIVE
  },
  [HistoryEventType.WITHDRAWAL]: {
    [HistoryEventSubType.REMOVE_ASSET]: TransactionEventType.WITHDRAW,
    [HistoryEventSubType.GENERATE_DEBT]: TransactionEventType.BORROW
  },
  [HistoryEventType.DEPOSIT]: {
    [HistoryEventSubType.DEPOSIT_ASSET]: TransactionEventType.DEPOSIT
  },
  [HistoryEventType.MIGRATE]: {
    [HistoryEventSubType.SPEND]: TransactionEventType.SEND,
    [HistoryEventSubType.RECEIVE]: TransactionEventType.RECEIVE
  }
};

export const transactionEventProtocolData: ActionDataEntry[] = [
  {
    identifier: TransactionEventProtocol.COMPOUND,
    label: 'Compound',
    image: require('@/assets/images/defi/compound.svg')
  },
  {
    identifier: TransactionEventProtocol.GITCOIN,
    label: 'Gitcoin',
    image: require('@/assets/images/gitcoin.svg')
  },
  {
    identifier: TransactionEventProtocol.XDAI,
    label: 'Aave',
    image: require('@/assets/images/defi/xdai.png')
  },
  {
    identifier: TransactionEventProtocol.MAKERDAO,
    label: 'Makerdao',
    image: require('@/assets/images/defi/makerdao.svg'),
    matcher: (identifier: string) =>
      identifier.toLowerCase().startsWith('makerdao')
  },
  {
    identifier: TransactionEventProtocol.UNISWAP,
    label: 'Uniswap',
    image: require('@/assets/images/defi/uniswap.svg'),
    matcher: (identifier: string) =>
      identifier.toLowerCase().startsWith('uniswap')
  },
  {
    identifier: TransactionEventProtocol.AAVE,
    label: 'Aave',
    image: require('@/assets/images/defi/aave.svg'),
    matcher: (identifier: string) => identifier.toLowerCase().startsWith('aave')
  },
  {
    identifier: TransactionEventProtocol['1INCH'],
    label: '1inch',
    image: require('@/assets/images/defi/1inch.svg'),
    matcher: (identifier: string) =>
      identifier.toLowerCase().startsWith('1inch')
  }
];
