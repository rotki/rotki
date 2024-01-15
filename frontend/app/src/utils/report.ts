import type {
  ProfitLossEvent,
  ProfitLossOverviewItem,
  SelectedReport,
} from '@/types/reports';

export function calculateTotalProfitLoss(item: SelectedReport): ProfitLossOverviewItem {
  let totalFree = Zero;
  let totalTaxable = Zero;
  for (const key in item.overview) {
    totalFree = totalFree.plus(item.overview[key].free);
    totalTaxable = totalTaxable.plus(item.overview[key].taxable);
  }

  return {
    free: totalFree,
    taxable: totalTaxable,
  };
}

// TODO: Figure out in the future, how to avoid hardcode
export function isTransactionEvent(item: ProfitLossEvent) {
  return item.type === 'transaction event';
}
