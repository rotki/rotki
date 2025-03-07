import type { AccountingRuleEntry } from '@/types/settings/accounting';
import { TimeFramePeriod, type TimeFrameSetting } from '@rotki/common';

export function isPeriodAllowed(period: TimeFrameSetting): boolean {
  return period === TimeFramePeriod.WEEK || period === TimeFramePeriod.TWO_WEEKS;
}

export function getPlaceholderRule(): AccountingRuleEntry {
  return {
    accountingTreatment: null,
    countCostBasisPnl: { value: false },
    countEntireAmountSpend: { value: false },
    counterparty: null,
    eventSubtype: '',
    eventType: '',
    identifier: -1,
    taxable: { value: false },
  };
}
