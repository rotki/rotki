import { AssetBalance } from './asset-balance';

export interface BlockchainAccountResult {
    readonly result: boolean;
    readonly message: string;
    readonly per_account: { [asset: string]: { [account: string]: AssetBalance } };
    readonly totals: { [asset: string]: AssetBalance };
}
