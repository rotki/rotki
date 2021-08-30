import { Nullable } from "../index";

export interface ActionResult<T> {
  readonly result: T;
  readonly message: string;
}

export interface BaseAsset {
  readonly identifier: string;
  readonly coingecko?: Nullable<string>;
  readonly cryptocompare?: string;
  readonly started?: Nullable<number>;
  readonly name: Nullable<string>;
  readonly symbol: string;
  readonly swappedFor?: Nullable<string>;
}

export interface SupportedAsset extends BaseAsset {
  readonly active?: boolean;
  readonly ended?: number | null;
  readonly decimals?: number | null;
  readonly assetType: string;
  readonly forked?: string | null;
  readonly ethereumAddress?: string | null;
}