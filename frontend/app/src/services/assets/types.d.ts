export interface UnderlyingToken {
  readonly address: string;
  readonly weight: string;
}

export interface EthereumToken {
  readonly identifier?: string;
  readonly address: string;
  readonly decimals: number;
  readonly name: string;
  readonly symbol: string;
  readonly started?: number;
  readonly coingecko?: string | null;
  readonly cryptocompare?: string;
  readonly underlyingTokens?: UnderlyingToken[];
  readonly swappedFor?: string;
  readonly protocol?: string;
}

export interface AssetIdResponse {
  readonly identifier: string;
}
