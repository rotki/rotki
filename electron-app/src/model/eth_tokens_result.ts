import {EthToken} from './eth_token';

export interface EthTokensResult {
    readonly all_eth_tokens: EthToken[];
    readonly owned_eth_tokens: string[];
}
