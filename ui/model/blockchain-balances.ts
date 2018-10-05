import {AssetBalance} from './asset-balance';

export interface BlockchainBalances {
    readonly per_account: { [asset: string]: { [account: string]: AssetBalance } };
    readonly totals: { [asset: string]: AssetBalance };
}
