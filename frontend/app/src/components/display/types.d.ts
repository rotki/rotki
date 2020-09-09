import { Balance } from '@/services/types-api';

export interface AssetMovement {
  readonly asset: string;
  readonly value: Balance;
  readonly toAsset: string;
  readonly toValue: Balance;
}
