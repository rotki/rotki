import { Balance } from '@rotki/common';

export interface AssetMovement {
  readonly asset: string;
  readonly value: Balance;
  readonly toAsset: string;
  readonly toValue: Balance;
}
