import { default as BigNumber } from 'bignumber.js';
import { CompoundProfitAndLoss } from '@/services/defi/types/compound';
import { HasBalance } from '@/services/types-api';
import { ProfitLossModel } from '@/store/defi/types';
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
