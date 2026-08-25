import type { MissingAcquisition, MissingPrice, Report, ReportActionableItem, Reports } from '@/modules/reports/report-types';
import type { BaseAccountingSettings } from '@/modules/settings/types/user-settings';
import { createMock } from '@test/utils/create-mock';

/**
 * Fixtures shared by the two `pages/reports/` specs. They sit together because the pair shares a
 * store and a navigation contract, not because the pages share logic.
 */

export const LATEST_REPORT_ID = 42;

export const OLDER_REPORT_ID = 7;

const PROFIT_CURRENCY = 'EUR';

/**
 * Concrete rather than mocked: the page hands this object straight to a child and a spec compares
 * it by value, which a `createMock` proxy cannot satisfy - two proxies are never deeply equal.
 */
export function createAccountingSettings(): BaseAccountingSettings {
  return {
    calculatePastCostBasis: true,
    costBasisMethod: undefined,
    includeCrypto2crypto: true,
    includeGasCosts: true,
    profitCurrency: PROFIT_CURRENCY,
    taxfreeAfterPeriod: undefined,
  };
}

/**
 * A report is a wide zod-inferred object of which these pages read five fields. `createMock` fills
 * the rest, so adding a field to the schema does not break every fixture here.
 */
export function createReport(overrides: Partial<Report> = {}): Report {
  return createMock<Report>({
    endTs: 1_600_100_000,
    identifier: LATEST_REPORT_ID,
    processedActions: 10,
    settings: createAccountingSettings(),
    startTs: 1_600_000_000,
    totalActions: 10,
    ...overrides,
  });
}

export function createReports(entries: Report[]): Reports {
  return {
    entries,
    entriesFound: entries.length,
    entriesLimit: entries.length,
  };
}

/**
 * The pages only ever count these, so the contents are irrelevant - what matters is the length.
 */
export function createMissingAcquisitions(count: number): MissingAcquisition[] {
  return Array.from({ length: count }, () => createMock<MissingAcquisition>({}));
}

export function createMissingPrices(count: number): MissingPrice[] {
  return Array.from({ length: count }, () => createMock<MissingPrice>({}));
}

export function createActionableItems(overrides: Partial<ReportActionableItem> = {}): ReportActionableItem {
  return {
    eventsSkippedNoRule: 0,
    missingAcquisitions: [],
    missingPrices: [],
    ...overrides,
  };
}
