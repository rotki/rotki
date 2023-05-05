import {
  type ProfitLossEvent,
  type ProfitLossOverviewItem,
  type SelectedReport
} from '@/types/reports';

export const calculateTotalProfitLoss = (
  item: SelectedReport
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

// TODO: Figure out in the future, how to avoid hardcode
export const isTransactionEvent = (item: ProfitLossEvent) =>
  item.type === 'transaction event';
