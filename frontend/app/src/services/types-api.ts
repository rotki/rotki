import { Location } from '@/services/types-common';

export interface ApiSupportedAsset {
  readonly active?: boolean;
  readonly ended?: number;
  readonly name: string;
  readonly started?: number;
  readonly symbol: string;
  readonly type: string;
}

export interface SupportedAssets {
  readonly [key: string]: ApiSupportedAsset;
}

export interface ApiManualBalance {
  readonly asset: string;
  readonly label: string;
  readonly amount: string;
  readonly location: Location;
  readonly tags: string[];
}

export interface ApiManualBalanceWithValue extends ApiManualBalance {
  readonly usd_value: string;
}

export interface ApiManualBalances {
  readonly balances: ApiManualBalanceWithValue[];
}

export class TaskNotFoundError extends Error {}
