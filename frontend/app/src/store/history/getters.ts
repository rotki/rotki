import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store/types';
import { HistoryState, TradeEntry } from './types';

export const getters: GetterTree<HistoryState, RotkehlchenState> = {
  assetMovements: ({ assetMovements }) => {
    return assetMovements.data;
  },
  assetMovementsTotal: ({ assetMovements }) => {
    return assetMovements.found;
  },
  assetMovementsLimit: ({ assetMovements }) => {
    return assetMovements.limit;
  },
  ledgerActions: ({ ledgerActions }) => {
    return ledgerActions.data;
  },
  ledgerActionsTotal: ({ ledgerActions }) => {
    return ledgerActions.found;
  },
  ledgerActionsLimit: ({ ledgerActions }) => {
    return ledgerActions.limit;
  },
  trades: ({ trades }, _, _rs, { 'defi/basicDexTrades': dexTrades }) => {
    let dxTrades: TradeEntry[] = [];
    if (trades.limit === -1) {
      dxTrades = dexTrades([]);
    }

    return trades.data.concat(...dxTrades);
  },
  tradesTotal: ({ trades }) => {
    return trades.found;
  },
  tradesLimit: ({ trades }) => {
    return trades.limit;
  }
};
