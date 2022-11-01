import { ComputedRef } from 'vue';
import { ActionDataEntry } from '@/store/types';
import { LedgerActionType } from '@/types/ledger-actions';
import {
  HistoryEventSubType,
  HistoryEventType,
  TransactionEventProtocol,
  TransactionEventType
} from '@/types/transaction';

export const useLedgerActionData = createSharedComposable(() => {
  const { tc } = useI18n();
  const ledgerActionsData = computed(() => [
    {
      identifier: LedgerActionType.ACTION_INCOME,
      label: tc('ledger_actions.actions.income')
    },
    {
      identifier: LedgerActionType.ACTION_LOSS,
      label: tc('ledger_actions.actions.loss')
    },
    {
      identifier: LedgerActionType.ACTION_DONATION,
      label: tc('ledger_actions.actions.donation')
    },
    {
      identifier: LedgerActionType.ACTION_EXPENSE,
      label: tc('ledger_actions.actions.expense')
    },
    {
      identifier: LedgerActionType.ACTION_DIVIDENDS,
      label: tc('ledger_actions.actions.dividends')
    },
    {
      identifier: LedgerActionType.ACTION_AIRDROP,
      label: tc('ledger_actions.actions.airdrop')
    },
    {
      identifier: LedgerActionType.ACTION_GIFT,
      label: tc('ledger_actions.actions.gift')
    },
    {
      identifier: LedgerActionType.ACTION_GRANT,
      label: tc('ledger_actions.actions.grant')
    }
  ]);
  return {
    ledgerActionsData
  };
});

export const useHistoryEventTypeData = createSharedComposable(() => {
  const { tc } = useI18n();
  const historyEventTypeData: ComputedRef<ActionDataEntry[]> = computed(() => [
    {
      identifier: HistoryEventType.TRADE,
      label: tc('transactions.events.history_event_type.trade')
    },
    {
      identifier: HistoryEventType.STAKING,
      label: tc('transactions.events.history_event_type.staking')
    },
    {
      identifier: HistoryEventType.DEPOSIT,
      label: tc('transactions.events.history_event_type.deposit')
    },
    {
      identifier: HistoryEventType.WITHDRAWAL,
      label: tc('transactions.events.history_event_type.withdrawal')
    },
    {
      identifier: HistoryEventType.TRANSFER,
      label: tc('transactions.events.history_event_type.transfer')
    },
    {
      identifier: HistoryEventType.SPEND,
      label: tc('transactions.events.history_event_type.spend')
    },
    {
      identifier: HistoryEventType.RECEIVE,
      label: tc('transactions.events.history_event_type.receive')
    },
    {
      identifier: HistoryEventType.ADJUSTMENT,
      label: tc('transactions.events.history_event_type.adjustment')
    },
    {
      identifier: HistoryEventType.UNKNOWN,
      label: tc('transactions.events.history_event_type.unknown')
    },
    {
      identifier: HistoryEventType.INFORMATIONAL,
      label: tc('transactions.events.history_event_type.informational')
    },
    {
      identifier: HistoryEventType.MIGRATE,
      label: tc('transactions.events.history_event_type.migrate')
    },
    {
      identifier: HistoryEventType.RENEW,
      label: tc('transactions.events.history_event_type.renew')
    }
  ]);

  const historyEventSubTypeData: ComputedRef<ActionDataEntry[]> = computed(
    () => [
      {
        identifier: HistoryEventSubType.NONE,
        label: tc('transactions.events.history_event_subtype.none')
      },
      {
        identifier: HistoryEventSubType.REWARD,
        label: tc('transactions.events.history_event_subtype.reward')
      },
      {
        identifier: HistoryEventSubType.DEPOSIT_ASSET,
        label: tc('transactions.events.history_event_subtype.deposit_asset')
      },
      {
        identifier: HistoryEventSubType.REMOVE_ASSET,
        label: tc('transactions.events.history_event_subtype.remove_asset')
      },
      {
        identifier: HistoryEventSubType.FEE,
        label: tc('transactions.events.history_event_subtype.fee')
      },
      {
        identifier: HistoryEventSubType.SPEND,
        label: tc('transactions.events.history_event_subtype.spend')
      },
      {
        identifier: HistoryEventSubType.RECEIVE,
        label: tc('transactions.events.history_event_subtype.receive')
      },
      {
        identifier: HistoryEventSubType.APPROVE,
        label: tc('transactions.events.history_event_subtype.approve')
      },
      {
        identifier: HistoryEventSubType.DEPLOY,
        label: tc('transactions.events.history_event_subtype.deploy')
      },
      {
        identifier: HistoryEventSubType.AIRDROP,
        label: tc('transactions.events.history_event_subtype.airdrop')
      },
      {
        identifier: HistoryEventSubType.BRIDGE,
        label: tc('transactions.events.history_event_subtype.bridge')
      },
      {
        identifier: HistoryEventSubType.GOVERNANCE_PROPOSE,
        label: tc(
          'transactions.events.history_event_subtype.governance_propose'
        )
      },
      {
        identifier: HistoryEventSubType.GENERATE_DEBT,
        label: tc('transactions.events.history_event_subtype.generate_debt')
      },
      {
        identifier: HistoryEventSubType.PAYBACK_DEBT,
        label: tc('transactions.events.history_event_subtype.payback_debt')
      },
      {
        identifier: HistoryEventSubType.RECEIVE_WRAPPED,
        label: tc('transactions.events.history_event_subtype.receive_wrapped')
      },
      {
        identifier: HistoryEventSubType.RETURN_WRAPPED,
        label: tc('transactions.events.history_event_subtype.return_wrapped')
      },
      {
        identifier: HistoryEventSubType.REWARD,
        label: tc('transactions.events.history_event_subtype.reward')
      },
      {
        identifier: HistoryEventSubType.NFT,
        label: tc('transactions.events.history_event_subtype.nft')
      }
    ]
  );

  return { historyEventTypeData, historyEventSubTypeData };
});

export const useTransactionEventTypeData = createSharedComposable(() => {
  const { tc } = useI18n();
  const transactionEventTypeData: ComputedRef<ActionDataEntry[]> = computed(
    () => [
      {
        identifier: TransactionEventType.GAS,
        label: tc('transactions.events.type.gas_fee'),
        icon: 'mdi-fire'
      },
      {
        identifier: TransactionEventType.SEND,
        label: tc('transactions.events.type.send'),
        icon: 'mdi-arrow-up'
      },
      {
        identifier: TransactionEventType.RECEIVE,
        label: tc('transactions.events.type.receive'),
        icon: 'mdi-arrow-down',
        color: 'green'
      },
      {
        identifier: TransactionEventType.SWAP_OUT,
        label: tc('transactions.events.type.swap_out'),
        icon: 'mdi-arrow-u-right-bottom'
      },
      {
        identifier: TransactionEventType.SWAP_IN,
        label: tc('transactions.events.type.swap_in'),
        icon: 'mdi-arrow-u-left-top',
        color: 'green'
      },
      {
        identifier: TransactionEventType.APPROVAL,
        label: tc('transactions.events.type.approval'),
        icon: 'mdi-lock-open-outline'
      },
      {
        identifier: TransactionEventType.DEPOSIT,
        label: tc('transactions.events.type.deposit'),
        icon: 'mdi-arrow-expand-up',
        color: 'green'
      },
      {
        identifier: TransactionEventType.WITHDRAW,
        label: tc('transactions.events.type.withdraw'),
        icon: 'mdi-arrow-expand-down'
      },
      {
        identifier: TransactionEventType.AIRDROP,
        label: tc('transactions.events.type.airdrop'),
        icon: 'mdi-airballoon-outline'
      },
      {
        identifier: TransactionEventType.BORROW,
        label: tc('transactions.events.type.borrow'),
        icon: 'mdi-hand-coin-outline'
      },
      {
        identifier: TransactionEventType.REPAY,
        label: tc('transactions.events.type.repay'),
        icon: 'mdi-history'
      },
      {
        identifier: TransactionEventType.DEPLOY,
        label: tc('transactions.events.type.deploy'),
        icon: 'mdi-swap-horizontal'
      },
      {
        identifier: TransactionEventType.BRIDGE,
        label: tc('transactions.events.type.bridge'),
        icon: 'mdi-bridge'
      },
      {
        identifier: TransactionEventType.GOVERNANCE_PROPOSE,
        label: tc('transactions.events.type.governance_propose'),
        icon: 'mdi-bank'
      },
      {
        identifier: TransactionEventType.DONATE,
        label: tc('transactions.events.type.donate'),
        icon: 'mdi-hand-heart-outline'
      },
      {
        identifier: TransactionEventType.RECEIVE_DONATION,
        label: tc('transactions.events.type.receive_donation'),
        icon: 'mdi-hand-heart-outline'
      },
      {
        identifier: TransactionEventType.RENEW,
        label: tc('transactions.events.type.renew'),
        icon: 'mdi-calendar-refresh'
      },
      {
        identifier: TransactionEventType.PLACE_ORDER,
        label: tc('transactions.events.type.place_order'),
        icon: 'mdi-briefcase-arrow-up-down'
      },
      {
        identifier: TransactionEventType.TRANSFER,
        label: tc('transactions.events.type.transfer'),
        icon: 'mdi-swap-horizontal'
      },
      {
        identifier: TransactionEventType.CLAIM_REWARD,
        label: tc('transactions.events.type.claim_reward'),
        icon: 'mdi-gift'
      }
    ]
  );

  return {
    transactionEventTypeData
  };
});

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
