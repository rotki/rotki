import { Balances, EthBalances } from '@/model/blockchain-balances';

export const state: BalanceState = {
  eth: {},
  btc: {},
  totals: {}
};

export interface BalanceState {
  eth: EthBalances;
  btc: Balances;
  totals: Balances;
}
