import { ProfitLossOverviewItem, Report } from '@/types/reports';
import { Zero } from '@/utils/bignumbers';

export const calculateTotalProfitLoss = (
  item: Report
): ProfitLossOverviewItem => {
  let totalFree = Zero;
  let totalTaxable = Zero;
  for (const key in item.overview) {
    totalFree = totalFree.plus(item.overview[key].free);
    totalTaxable = totalTaxable.plus(item.overview[key].taxable);
  }

  return {
    free: totalFree,
    taxable: totalTaxable
  };
};
