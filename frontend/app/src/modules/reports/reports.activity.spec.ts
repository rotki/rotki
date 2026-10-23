import { describe, expect, it } from 'vitest';
import { pnlReportActivity, pnlReportExportActivity, pnlReportImportActivity } from '@/modules/reports/reports.activity';

describe('report activity ids', () => {
  it('should give report generation the bare kind', () => {
    expect(pnlReportActivity.id()).toBe('pnl-report');
    expect(pnlReportActivity.partsOf()).toStrictEqual([]);
  });

  it('should give export and import ids of their own, so a lookup by id tells them from generation', () => {
    expect(pnlReportExportActivity.id()).toBe('pnl-report:export');
    expect(pnlReportImportActivity.id()).toBe('pnl-report:import');
  });
});
