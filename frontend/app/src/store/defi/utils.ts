import { default as BigNumber } from 'bignumber.js';
import { TokenDetails } from '@/services/defi/types';
import { CompoundProfitAndLoss } from '@/services/defi/types/compound';
import { HasBalance } from '@/services/types-api';
import { AssetInfoGetter } from '@/store/balances/types';
import { ProfitLossModel } from '@/store/defi/types';
import store from '@/store/store';
import { Zero } from '@/utils/bignumbers';

export function balanceUsdValueSum(balances: HasBalance[]): BigNumber {
  return balances
    .map(({ balance: { usdValue } }) => usdValue)
    .reduce((sum, value) => sum.plus(value), Zero);
}

export function toProfitLossModel(
  profitAndLoss: CompoundProfitAndLoss
): ProfitLossModel[] {
  const data: ProfitLossModel[] = [];
  for (const address of Object.keys(profitAndLoss)) {
    const assets = profitAndLoss[address];
    for (const asset of Object.keys(assets)) {
      data.push({
        address,
        asset,
        value: assets[asset]
      });
    }
  }

  return data;
}

export function assetName(identifier: TokenDetails, symbol: boolean = false) {
  if (typeof identifier === 'string') {
    if (symbol) {
      const assetInfo = store.getters['balances/assetInfo'] as AssetInfoGetter;
      return assetInfo(identifier)?.symbol ?? identifier;
    }
    return identifier;
  }
  return identifier.symbol;
}
