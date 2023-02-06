import { type ProfitLossModel } from '@rotki/common/lib/defi';
import { type CompoundProfitAndLoss } from '@/types/defi/compound';

export const toProfitLossModel = (
  profitAndLoss: CompoundProfitAndLoss
): ProfitLossModel[] => {
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
};
