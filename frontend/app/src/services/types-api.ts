import { Location, TradeType } from '@/services/types-common';

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

export interface ApiTrade {
  readonly trade_id?: string;
  readonly timestamp: number;
  readonly location: string;
  readonly pair: string;
  readonly trade_type: TradeType;
  readonly amount: string;
  readonly rate: string;
  readonly fee: string;
  readonly fee_currency: string;
  readonly link: string;
  readonly notes: string;
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
