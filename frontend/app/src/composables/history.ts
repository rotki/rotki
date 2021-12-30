import { computed, Ref } from '@vue/composition-api';
import {
  AssetMovementRequestPayload,
  LedgerActionRequestPayload,
  NewLedgerAction,
  NewTrade,
  TradeLocation,
  TradeRequestPayload,
  TransactionRequestPayload
} from '@/services/history/types';
import { HistoryActions } from '@/store/history/consts';
import {
  AssetMovementEntry,
  EthTransactionEntry,
  LedgerActionEntry,
  TradeEntry
} from '@/store/history/types';
import { useStore } from '@/store/utils';

export const setupAssociatedLocations = () => {
  const store = useStore();
  const associatedLocations = computed<TradeLocation[]>(() => {
    return store.getters['history/associatedLocations'];
  });

  const fetchAssociatedLocations = async () => {
    return await store.dispatch(
      `history/${HistoryActions.FETCH_ASSOCIATED_LOCATIONS}`
    );
  };

  return { associatedLocations, fetchAssociatedLocations };
};

export const setupTrades = () => {
  const store = useStore();

  const trades = computed<TradeEntry[]>(() => {
    return store.getters['history/trades'];
  });
  const limit = computed<number>(() => {
    return store.getters['history/tradesLimit'];
  });
  const found = computed<number>(() => {
    return store.getters['history/tradesFound'];
  });
  const total = computed<number>(() => {
    return store.getters['history/tradesTotal'];
  });

  const fetchTrades = async (payload: Partial<TradeRequestPayload>) => {
    return await store.dispatch(`history/${HistoryActions.FETCH_TRADES}`, {
      payload
    });
  };

  const addTrade = async (trade: NewTrade) => {
    return await store.dispatch(
      `history/${HistoryActions.ADD_EXTERNAL_TRADE}`,
      trade
    );
  };

  const editTrade = async (trade: TradeEntry) => {
    return await store.dispatch(
      `history/${HistoryActions.EDIT_EXTERNAL_TRADE}`,
      trade
    );
  };

  const deleteTrade = async (tradeId: string) => {
    return await store.dispatch(
      `history/${HistoryActions.DELETE_EXTERNAL_TRADE}`,
      tradeId
    );
  };

  return {
    trades,
    limit,
    found,
    total,
    fetchTrades,
    addTrade,
    editTrade,
    deleteTrade
  };
};

export const setupAssetMovements = () => {
  const store = useStore();

  const assetMovements = computed<AssetMovementEntry[]>(() => {
    return store.getters['history/assetMovements'];
  });
  const limit = computed<number>(() => {
    return store.getters['history/assetMovementsLimit'];
  });
  const found = computed<number>(() => {
    return store.getters['history/assetMovementsFound'];
  });
  const total = computed<number>(() => {
    return store.getters['history/assetMovementsTotal'];
  });

  const fetchAssetMovements = async (
    payload: Partial<AssetMovementRequestPayload>
  ) => {
    return await store.dispatch(`history/${HistoryActions.FETCH_MOVEMENTS}`, {
      payload
    });
  };

  return {
    assetMovements,
    limit,
    found,
    total,
    fetchAssetMovements
  };
};

export const setupTransactions = () => {
  const store = useStore();

  const transactions = computed<EthTransactionEntry[]>(() => {
    return store.getters['history/transactions'];
  });
  const limit = computed<number>(() => {
    return store.getters['history/transactionsLimit'];
  });
  const found = computed<number>(() => {
    return store.getters['history/transactionsFound'];
  });
  const total = computed<number>(() => {
    return store.getters['history/transactionsTotal'];
  });

  const fetchTransactions = async (
    payload: Partial<TransactionRequestPayload>
  ) => {
    return await store.dispatch(
      `history/${HistoryActions.FETCH_TRANSACTIONS}`,
      payload
    );
  };

  return {
    transactions,
    limit,
    found,
    total,
    fetchTransactions
  };
};

export const setupLedgerActions = () => {
  const store = useStore();

  const ledgerActions = computed<LedgerActionEntry[]>(() => {
    return store.getters['history/ledgerActions'];
  });
  const limit = computed<number>(() => {
    return store.getters['history/ledgerActionsLimit'];
  });
  const found = computed<number>(() => {
    return store.getters['history/ledgerActionsFound'];
  });
  const total = computed<number>(() => {
    return store.getters['history/ledgerActionsTotal'];
  });

  const fetchLedgerActions = async (
    payload: Partial<LedgerActionRequestPayload>
  ) => {
    return await store.dispatch(
      `history/${HistoryActions.FETCH_LEDGER_ACTIONS}`,
      { payload }
    );
  };

  const addLedgerAction = async (ledgerAction: NewLedgerAction) => {
    return await store.dispatch(
      `history/${HistoryActions.ADD_LEDGER_ACTION}`,
      ledgerAction
    );
  };

  const editLedgerAction = async (ledgerAction: LedgerActionEntry) => {
    return await store.dispatch(
      `history/${HistoryActions.EDIT_LEDGER_ACTION}`,
      ledgerAction
    );
  };

  const deleteLedgerAction = async (identifier: number) => {
    return await store.dispatch(
      `history/${HistoryActions.DELETE_LEDGER_ACTION}`,
      identifier
    );
  };

  return {
    ledgerActions,
    limit,
    found,
    total,
    fetchLedgerActions,
    addLedgerAction,
    editLedgerAction,
    deleteLedgerAction
  };
};

export const setupEntryLimit = (
  limit: Ref<number>,
  found: Ref<number>,
  total: Ref<number>
) => {
  const store = useStore();

  const premium = computed(() => {
    return store.state.session!!.premium;
  });

  const itemLength = computed(() => {
    const isPremium = premium.value;
    const totalFound = found.value;
    if (isPremium) {
      return totalFound;
    }

    const entryLimit = limit.value;
    return Math.min(totalFound, entryLimit);
  });

  const showUpgradeRow = computed(() => {
    return limit.value <= total.value && limit.value > 0;
  });

  return {
    itemLength,
    showUpgradeRow
  };
};
