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

/**
 * Whether processing of a report stopped at the plan's event limit.
 *
 * @remarks
 * A report stores only the events it processed, so the cut shows only in its own action counts. A
 * missing price also leaves actions unprocessed, which is why reaching the limit is required too.
 *
 * @param report - the report whose action counts are checked
 * @param planLimit - the plan's event limit; 0 or less means the plan has none
 */
export function stoppedAtPlanLimit(report: Pick<Report, 'processedActions' | 'totalActions'>, planLimit: number): boolean {
  return planLimit > 0 && report.processedActions >= planLimit && report.processedActions < report.totalActions;
}
