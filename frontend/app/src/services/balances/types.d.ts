import { default as BigNumber } from 'bignumber.js';
import { exchanges } from '@/data/defaults';
import { Location } from '@/services/types-common';

export type SupportedExchange = typeof exchanges[number];

export interface ManualBalance {
  readonly asset: string;
  readonly label: string;
  readonly amount: BigNumber;
  readonly location: Location;
  readonly tags: string[];
}

export interface ManualBalanceWithValue extends ManualBalance {
  readonly usdValue: BigNumber;
}

export interface ManualBalances {
  readonly balances: ManualBalanceWithValue[];
}
