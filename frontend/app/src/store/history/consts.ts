import i18n from '@/i18n';
import { ActionDataEntry } from '@/store/types';
import { LedgerActionType } from '@/types/ledger-actions';
import {
  HistoryEventSubType,
  HistoryEventType,
  TransactionEventProtocol,
  TransactionEventType
} from '@/types/transaction';

export const ledgerActionsData = computed(() => [
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
]);

export const historyEventTypeData = computed<ActionDataEntry[]>(() => [
  {
    identifier: HistoryEventType.TRADE,
    label: i18n.t('transactions.events.history_event_type.trade').toString()
  },
  {
    identifier: HistoryEventType.STAKING,
    label: i18n.t('transactions.events.history_event_type.staking').toString()
  },
  {
    identifier: HistoryEventType.DEPOSIT,
    label: i18n.t('transactions.events.history_event_type.deposit').toString()
  },
  {
    identifier: HistoryEventType.WITHDRAWAL,
    label: i18n
      .t('transactions.events.history_event_type.withdrawal')
      .toString()
  },
  {
    identifier: HistoryEventType.TRANSFER,
    label: i18n.t('transactions.events.history_event_type.transfer').toString()
  },
  {
    identifier: HistoryEventType.SPEND,
    label: i18n.t('transactions.events.history_event_type.spend').toString()
  },
  {
    identifier: HistoryEventType.RECEIVE,
    label: i18n.t('transactions.events.history_event_type.receive').toString()
  },
  {
    identifier: HistoryEventType.ADJUSTMENT,
    label: i18n
      .t('transactions.events.history_event_type.adjustment')
      .toString()
  },
  {
    identifier: HistoryEventType.UNKNOWN,
    label: i18n.t('transactions.events.history_event_type.unknown').toString()
  },
  {
    identifier: HistoryEventType.INFORMATIONAL,
    label: i18n
      .t('transactions.events.history_event_type.informational')
      .toString()
  },
  {
    identifier: HistoryEventType.MIGRATE,
    label: i18n.t('transactions.events.history_event_type.migrate').toString()
  },
  {
    identifier: HistoryEventType.RENEW,
    label: i18n.t('transactions.events.history_event_type.renew').toString()
  }
]);

export const historyEventSubTypeData = computed<ActionDataEntry[]>(() => [
  {
    identifier: HistoryEventSubType.NONE,
    label: i18n.t('transactions.events.history_event_subtype.none').toString()
  },
  {
    identifier: HistoryEventSubType.REWARD,
    label: i18n.t('transactions.events.history_event_subtype.reward').toString()
  },
  {
    identifier: HistoryEventSubType.DEPOSIT_ASSET,
    label: i18n
      .t('transactions.events.history_event_subtype.deposit_asset')
      .toString()
  },
  {
    identifier: HistoryEventSubType.REMOVE_ASSET,
    label: i18n
      .t('transactions.events.history_event_subtype.remove_asset')
      .toString()
  },
  {
    identifier: HistoryEventSubType.FEE,
    label: i18n.t('transactions.events.history_event_subtype.fee').toString()
  },
  {
    identifier: HistoryEventSubType.SPEND,
    label: i18n.t('transactions.events.history_event_subtype.spend').toString()
  },
  {
    identifier: HistoryEventSubType.RECEIVE,
    label: i18n
      .t('transactions.events.history_event_subtype.receive')
      .toString()
  },
  {
    identifier: HistoryEventSubType.APPROVE,
    label: i18n
      .t('transactions.events.history_event_subtype.approve')
      .toString()
  },
  {
    identifier: HistoryEventSubType.DEPLOY,
    label: i18n.t('transactions.events.history_event_subtype.deploy').toString()
  },
  {
    identifier: HistoryEventSubType.AIRDROP,
    label: i18n
      .t('transactions.events.history_event_subtype.airdrop')
      .toString()
  },
  {
    identifier: HistoryEventSubType.BRIDGE,
    label: i18n.t('transactions.events.history_event_subtype.bridge').toString()
  },
  {
    identifier: HistoryEventSubType.GOVERNANCE_PROPOSE,
    label: i18n
      .t('transactions.events.history_event_subtype.governance_propose')
      .toString()
  },
  {
    identifier: HistoryEventSubType.GENERATE_DEBT,
    label: i18n
      .t('transactions.events.history_event_subtype.generate_debt')
      .toString()
  },
  {
    identifier: HistoryEventSubType.PAYBACK_DEBT,
    label: i18n
      .t('transactions.events.history_event_subtype.payback_debt')
      .toString()
  },
  {
    identifier: HistoryEventSubType.RECEIVE_WRAPPED,
    label: i18n
      .t('transactions.events.history_event_subtype.receive_wrapped')
      .toString()
  },
  {
    identifier: HistoryEventSubType.RETURN_WRAPPED,
    label: i18n
      .t('transactions.events.history_event_subtype.return_wrapped')
      .toString()
  },
  {
    identifier: HistoryEventSubType.REWARD,
    label: i18n.t('transactions.events.history_event_subtype.reward').toString()
  },
  {
    identifier: HistoryEventSubType.NFT,
    label: i18n.t('transactions.events.history_event_subtype.nft').toString()
  }
]);

export const transactionEventTypeData = computed<ActionDataEntry[]>(() => [
  {
    identifier: TransactionEventType.GAS,
    label: i18n.t('transactions.events.type.gas_fee').toString(),
    icon: 'mdi-fire'
  },
  {
    identifier: TransactionEventType.SEND,
    label: i18n.t('transactions.events.type.send').toString(),
    icon: 'mdi-arrow-up'
  },
  {
    identifier: TransactionEventType.RECEIVE,
    label: i18n.t('transactions.events.type.receive').toString(),
    icon: 'mdi-arrow-down',
    color: 'green'
  },
  {
    identifier: TransactionEventType.SWAP_OUT,
    label: i18n.t('transactions.events.type.swap_out').toString(),
    icon: 'mdi-arrow-u-right-bottom'
  },
  {
    identifier: TransactionEventType.SWAP_IN,
    label: i18n.t('transactions.events.type.swap_in').toString(),
    icon: 'mdi-arrow-u-left-top',
    color: 'green'
  },
  {
    identifier: TransactionEventType.APPROVAL,
    label: i18n.t('transactions.events.type.approval').toString(),
    icon: 'mdi-lock-open-outline'
  },
  {
    identifier: TransactionEventType.DEPOSIT,
    label: i18n.t('transactions.events.type.deposit').toString(),
    icon: 'mdi-arrow-expand-up',
    color: 'green'
  },
  {
    identifier: TransactionEventType.WITHDRAW,
    label: i18n.t('transactions.events.type.withdraw').toString(),
    icon: 'mdi-arrow-expand-down'
  },
  {
    identifier: TransactionEventType.AIRDROP,
    label: i18n.t('transactions.events.type.airdrop').toString(),
    icon: 'mdi-airballoon-outline'
  },
  {
    identifier: TransactionEventType.BORROW,
    label: i18n.t('transactions.events.type.borrow').toString(),
    icon: 'mdi-hand-coin-outline'
  },
  {
    identifier: TransactionEventType.REPAY,
    label: i18n.t('transactions.events.type.repay').toString(),
    icon: 'mdi-history'
  },
  {
    identifier: TransactionEventType.DEPLOY,
    label: i18n.t('transactions.events.type.deploy').toString(),
    icon: 'mdi-swap-horizontal'
  },
  {
    identifier: TransactionEventType.BRIDGE,
    label: i18n.t('transactions.events.type.bridge').toString(),
    icon: 'mdi-bridge'
  },
  {
    identifier: TransactionEventType.GOVERNANCE_PROPOSE,
    label: i18n.t('transactions.events.type.governance_propose').toString(),
    icon: 'mdi-bank'
  },
  {
    identifier: TransactionEventType.DONATE,
    label: i18n.t('transactions.events.type.donate').toString(),
    icon: 'mdi-hand-heart-outline'
  },
  {
    identifier: TransactionEventType.RECEIVE_DONATION,
    label: i18n.t('transactions.events.type.receive_donation').toString(),
    icon: 'mdi-hand-heart-outline'
  },
  {
    identifier: TransactionEventType.RENEW,
    label: i18n.t('transactions.events.type.renew').toString(),
    icon: 'mdi-calendar-refresh'
  },
  {
    identifier: TransactionEventType.PLACE_ORDER,
    label: i18n.t('transactions.events.type.place_order').toString(),
    icon: 'mdi-briefcase-arrow-up-down'
  },
  {
    identifier: TransactionEventType.TRANSFER,
    label: i18n.t('transactions.events.type.transfer').toString(),
    icon: 'mdi-swap-horizontal'
  },
  {
    identifier: TransactionEventType.CLAIM_REWARD,
    label: i18n.t('transactions.events.type.claim_reward').toString(),
    icon: 'mdi-gift'
  }
]);

export const transactionEventTypeMapping: {
  [type: string]: { [subType: string]: TransactionEventType };
} = {
  [HistoryEventType.SPEND]: {
    [HistoryEventSubType.FEE]: TransactionEventType.GAS,
    [HistoryEventSubType.PAYBACK_DEBT]: TransactionEventType.REPAY,
    [HistoryEventSubType.RETURN_WRAPPED]: TransactionEventType.SEND,
    [HistoryEventSubType.DONATE]: TransactionEventType.DONATE,
    [HistoryEventSubType.NONE]: TransactionEventType.SEND
  },
  [HistoryEventType.RECEIVE]: {
    [HistoryEventSubType.GENERATE_DEBT]: TransactionEventType.BORROW,
    [HistoryEventSubType.RECEIVE_WRAPPED]: TransactionEventType.RECEIVE,
    [HistoryEventSubType.RETURN_WRAPPED]: TransactionEventType.RECEIVE,
    [HistoryEventSubType.AIRDROP]: TransactionEventType.AIRDROP,
    [HistoryEventSubType.REWARD]: TransactionEventType.CLAIM_REWARD,
    [HistoryEventSubType.NONE]: TransactionEventType.RECEIVE,
    [HistoryEventSubType.DONATE]: TransactionEventType.RECEIVE_DONATION
  },
  [HistoryEventType.INFORMATIONAL]: {
    [HistoryEventSubType.APPROVE]: TransactionEventType.APPROVAL,
    [HistoryEventSubType.GOVERNANCE_PROPOSE]:
      TransactionEventType.GOVERNANCE_PROPOSE,
    [HistoryEventSubType.DEPLOY]: TransactionEventType.DEPLOY,
    [HistoryEventSubType.REMOVE_ASSET]: TransactionEventType.WITHDRAW,
    [HistoryEventSubType.PLACE_ORDER]: TransactionEventType.PLACE_ORDER
  },
  [HistoryEventType.TRANSFER]: {
    [HistoryEventSubType.BRIDGE]: TransactionEventType.BRIDGE,
    [HistoryEventSubType.NONE]: TransactionEventType.TRANSFER
  },
  [HistoryEventType.TRADE]: {
    [HistoryEventSubType.SPEND]: TransactionEventType.SWAP_OUT,
    [HistoryEventSubType.RECEIVE]: TransactionEventType.SWAP_IN
  },
  [HistoryEventType.WITHDRAWAL]: {
    [HistoryEventSubType.NONE]: TransactionEventType.WITHDRAW,
    [HistoryEventSubType.REMOVE_ASSET]: TransactionEventType.WITHDRAW,
    [HistoryEventSubType.GENERATE_DEBT]: TransactionEventType.BORROW
  },
  [HistoryEventType.DEPOSIT]: {
    [HistoryEventSubType.NONE]: TransactionEventType.DEPOSIT,
    [HistoryEventSubType.DEPOSIT_ASSET]: TransactionEventType.DEPOSIT,
    [HistoryEventSubType.BRIDGE]: TransactionEventType.DEPOSIT
  },
  [HistoryEventType.MIGRATE]: {
    [HistoryEventSubType.SPEND]: TransactionEventType.SEND,
    [HistoryEventSubType.RECEIVE]: TransactionEventType.RECEIVE
  },
  [HistoryEventType.RENEW]: {
    [HistoryEventSubType.NFT]: TransactionEventType.RENEW
  }
};

export const transactionEventProtocolData = computed<ActionDataEntry[]>(() => [
  {
    identifier: TransactionEventProtocol.COMPOUND,
    label: 'Compound',
    image: '/assets/images/defi/compound.svg'
  },
  {
    identifier: TransactionEventProtocol.GITCOIN,
    label: 'Gitcoin',
    image: '/assets/images/gitcoin.svg'
  },
  {
    identifier: TransactionEventProtocol.XDAI,
    label: 'Aave',
    image: '/assets/images/defi/xdai.png'
  },
  {
    identifier: TransactionEventProtocol.MAKERDAO,
    label: 'Makerdao',
    image: '/assets/images/defi/makerdao.svg',
    matcher: (identifier: string) =>
      identifier.toLowerCase().startsWith('makerdao')
  },
  {
    identifier: TransactionEventProtocol.UNISWAP,
    label: 'Uniswap',
    image: '/assets/images/defi/uniswap.svg',
    matcher: (identifier: string) =>
      identifier.toLowerCase().startsWith('uniswap')
  },
  {
    identifier: TransactionEventProtocol.SUSHISWAP,
    label: 'Sushiswap',
    image: '/assets/images/defi/sushi.png',
    matcher: (identifier: string) =>
      identifier.toLowerCase().startsWith('sushiswap')
  },
  {
    identifier: TransactionEventProtocol.AAVE,
    label: 'Aave',
    image: '/assets/images/defi/aave.svg',
    matcher: (identifier: string) => identifier.toLowerCase().startsWith('aave')
  },
  {
    identifier: TransactionEventProtocol.FRAX,
    label: 'FRAX',
    image: '/assets/images/defi/frax.png'
  },
  {
    identifier: TransactionEventProtocol.CONVEX,
    label: 'Convex',
    image: '/assets/images/defi/convex.jpeg'
  },
  {
    identifier: TransactionEventProtocol['1INCH'],
    label: '1inch',
    image: '/assets/images/defi/1inch.svg',
    matcher: (identifier: string) =>
      identifier.toLowerCase().startsWith('1inch')
  },
  {
    identifier: TransactionEventProtocol.ZKSYNC,
    label: 'zkSync',
    image: '/assets/images/zksync.jpg'
  },
  {
    identifier: TransactionEventProtocol.VOTIUM,
    label: 'Votium',
    image: '/assets/images/defi/votium.png'
  },
  {
    identifier: TransactionEventProtocol.LIQUITY,
    label: 'Liquity',
    image: '/assets/images/defi/liquity.svg'
  },
  {
    identifier: TransactionEventProtocol.CURVE,
    label: 'Curve.fi',
    image: '/assets/images/defi/curve.svg'
  },
  {
    identifier: TransactionEventProtocol.SHAPESHIFT,
    label: 'Shapeshift',
    image: '/assets/images/shapeshift.svg'
  },
  {
    identifier: TransactionEventProtocol.PICKLE,
    label: 'Pickle Finance',
    image: '/assets/images/modules/pickle.svg'
  },
  {
    identifier: TransactionEventProtocol.DXDAO,
    label: 'dxdao',
    image: '/assets/images/defi/dxdao.svg',
    matcher: (identifier: string) =>
      identifier.toLowerCase().startsWith('dxdao')
  },
  {
    identifier: TransactionEventProtocol.BADGER,
    label: 'badger',
    image: '/assets/images/defi/badger.png'
  },
  {
    identifier: TransactionEventProtocol.ENS,
    label: 'ens',
    image: '/assets/images/airdrops/ens.svg'
  },
  {
    identifier: TransactionEventProtocol.KRAKEN,
    label: 'kraken',
    image: '/assets/images/exchanges/kraken.svg'
  },
  {
    identifier: TransactionEventProtocol.ELEMENT_FINANCE,
    label: 'Element Finance',
    image: '/assets/images/defi/element_finance.png'
  },
  {
    identifier: TransactionEventProtocol.HOP_PROTOCOL,
    label: 'Hop Protocol',
    image: '/assets/images/hop_protocol.png'
  },
  {
    identifier: TransactionEventProtocol.WETH,
    label: 'WETH',
    image: '/assets/images/defi/weth.svg'
  }
]);
