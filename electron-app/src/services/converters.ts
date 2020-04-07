import { default as BigNumber } from 'bignumber.js';
import { ApiDSRBalances, ApiDSRHistory } from '@/services/types-api';
import { DSRBalances, DSRHistory, DSRMovement } from '@/services/types-model';
import { bigNumberify } from '@/utils/bignumbers';

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
  const data: {
    [address: string]: {
      movements: DSRMovement[];
      gainSoFar: BigNumber;
    };
  } = {};
  for (const account of Object.keys(history)) {
    const { gain_so_far: accountGain, movements } = history[account];
    data[account] = {
      gainSoFar: bigNumberify(accountGain),
      movements: movements.map(
        ({
          amount,
          block_number,
          gain_so_far: gain_so_far,
          movement_type,
          timestamp
        }) => ({
          movementType: movement_type,
          gainSoFar: bigNumberify(gain_so_far),
          amount: bigNumberify(amount),
          blockNumber: block_number,
          timestamp
        })
      )
    };
  }
  return data;
}
