import { ApiDSRBalances, ApiDSRHistory } from '@/services/types-api';
import { DSRBalances, DSRHistory, DSRMovement } from '@/services/types-model';
import { bigNumberify } from '@/utils/bignumbers';
import BigNumber from 'bignumber.js';

export function convertDSRBalances({
  balances,
  current_dsr
}: ApiDSRBalances): DSRBalances {
  const data: { [account: string]: BigNumber } = {};
  for (const account of Object.keys(balances)) {
    data[account] = bigNumberify(balances[account]);
  }
  return {
    currentDSR: bigNumberify(current_dsr),
    balances: data
  };
}

export function convertDSRHistory(history: ApiDSRHistory): DSRHistory {
  const data: { [address: string]: DSRMovement } = {};
  for (const account of Object.keys(history)) {
    const {
      movement_type,
      gain_so_far,
      amount,
      block_number,
      timestamp
    } = history[account];
    data[account] = {
      movementType: movement_type,
      gainSoFar: bigNumberify(gain_so_far),
      amount: bigNumberify(amount),
      blockNumber: block_number,
      timestamp
    };
  }
  return data;
}
