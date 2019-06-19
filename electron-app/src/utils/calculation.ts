import { AssetBalance } from '@/model/asset-balance';

export function assetSum(balances: { [asset: string]: AssetBalance }) {
  let value = 0;
  for (const asset in balances) {
    if (balances.hasOwnProperty(asset)) {
      value += parseFloat(balances[asset].usd_value.toString());
    }
  }
  return value;
}
