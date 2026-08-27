import type { ProfitLossEvent, ProfitLossOverviewItem, Report } from '@/modules/reports/report-types';
import { Zero } from '@rotki/common';

export function calculateTotalProfitLoss(item: Report): ProfitLossOverviewItem {
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

const TRANSACTION_EVENT_TYPE = 'transaction event'; // TODO: read this from the backend instead

export function isTransactionEvent(item: ProfitLossEvent): boolean {
  return item.type === TRANSACTION_EVENT_TYPE;
}
