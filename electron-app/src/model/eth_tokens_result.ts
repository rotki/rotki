import { EthToken } from './eth_token';

export interface EthTokens {
  readonly all_eth_tokens: EthToken[];
  readonly owned_eth_tokens: string[];
}
