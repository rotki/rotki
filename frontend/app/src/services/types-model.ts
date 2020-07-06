import { default as BigNumber } from 'bignumber.js';
import { Location } from '@/services/types-common';

export interface ManualBalance {
  readonly asset: string;
  readonly label: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
  readonly location: Location;
  readonly tags: string[];
}

export interface SupportedAsset {
  readonly key: string;
  readonly active?: boolean;
  readonly ended?: number;
  readonly name: string;
  readonly started?: number;
  readonly symbol: string;
  readonly type: string;
}
