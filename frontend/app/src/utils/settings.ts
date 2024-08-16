import { TimeFramePeriod, type TimeFrameSetting } from '@rotki/common';
import type { AccountingRuleEntry } from '@/types/settings/accounting';

export function isPeriodAllowed(period: TimeFrameSetting): boolean {
  return period === TimeFramePeriod.WEEK || period === TimeFramePeriod.TWO_WEEKS;
}

export function getPlaceholderRule(): AccountingRuleEntry {
  return {
    identifier: -1,
    eventType: '',
    eventSubtype: '',
    counterparty: null,
    taxable: { value: false },
    countEntireAmountSpend: { value: false },
    countCostBasisPnl: { value: false },
    accountingTreatment: null,
  };
}
