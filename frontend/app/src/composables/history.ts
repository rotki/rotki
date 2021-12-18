import { computed } from '@vue/composition-api';
import {
  NewTrade,
  TradeLocation,
  TradeRequestPayload,
  TransactionRequestPayload
} from '@/services/history/types';
import { HistoryActions } from '@/store/history/consts';
import { EthTransactionEntry, TradeEntry } from '@/store/history/types';
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
    return await store.dispatch(
      `history/${HistoryActions.FETCH_TRADES}`,
      payload
    );
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
