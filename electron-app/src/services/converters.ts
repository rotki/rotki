import { ApiDSRBalances, ApiDSRHistory } from '@/services/types-api';
import { DSRBalances, DSRHistory } from '@/services/types-model';
import { bigNumberify } from '@/utils/bignumbers';

export function convertDSRBalances(balances: ApiDSRBalances): DSRBalances {
  const data: DSRBalances = {};
  for (const account of Object.keys(balances)) {
    data[account] = bigNumberify(balances[account]);
  }
  return data;
}

export function convertDSRHistory(history: ApiDSRHistory): DSRHistory {
  const data: DSRHistory = {};
  for (const account of Object.keys(history)) {
    const { movement_type, gain_so_far, amount, block_number } = history[
      account
    ];
    data[account] = {
      movementType: movement_type,
      gainSoFar: bigNumberify(gain_so_far),
      amount: bigNumberify(amount),
      blockNumber: block_number
    };
  }
  return data;
}
