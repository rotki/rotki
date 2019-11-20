// This is equivalent to python's AssetBalance named tuple
export interface DBAssetBalance {
  readonly time: number;
  readonly asset: string;
  readonly amount: string;
  readonly usd_value: string;
}
