export interface EthToken {
  readonly address: string;
  readonly symbol: string;
  readonly name: string;
  readonly decimal: number;
  readonly type: string;
}

export interface EthTokens {
  readonly all_eth_tokens: EthToken[];
  readonly owned_eth_tokens: string[];
}
