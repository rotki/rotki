import { AssetBalance } from './asset-balance';

export interface ExchangeBalanceResult {
    readonly name: string;
    readonly error?: string;
    readonly balances?: { [asset: string]: AssetBalance };
}