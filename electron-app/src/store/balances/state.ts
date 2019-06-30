import {
  ApiBalances,
  Balances,
  EthBalances
} from '@/model/blockchain-balances';
import BigNumber from 'bignumber.js';
import { Zero } from '@/utils/bignumbers';

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
