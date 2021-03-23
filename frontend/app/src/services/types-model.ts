export interface SupportedAsset {
  readonly identifier: string;
  readonly coingecko?: string | null;
  readonly cryptocompare?: string;
  readonly active?: boolean;
  readonly ended?: number | null;
  readonly decimals?: number | null;
  readonly name: string;
  readonly started?: number | null;
  readonly symbol: string;
  readonly assetType: string;
  readonly swappedFor?: string | null;
  readonly forked?: string | null;
  readonly ethereumAddress?: string | null;
}
