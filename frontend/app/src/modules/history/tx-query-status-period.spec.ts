import { describe, expect, it } from 'vitest';
import { periodSteps } from '@/modules/history/tx-query-status-period';

describe('periodSteps', () => {
  it('should measure the cursor against the established window', () => {
    expect(periodSteps({ originalPeriodEnd: 200, originalPeriodStart: 100, period: [100, 150] }))
      .toStrictEqual({ current: 50, total: 100 });
  });

  it('should fall back to the period start when no original start was captured', () => {
    expect(periodSteps({ originalPeriodEnd: 200, period: [100, 125] }))
      .toStrictEqual({ current: 25, total: 100 });
  });

  it('should report nothing for a query that sends no period', () => {
    expect(periodSteps({ originalPeriodEnd: 200 })).toBeUndefined();
  });

  it('should report nothing before the target has been established', () => {
    expect(periodSteps({ period: [100, 150] })).toBeUndefined();
  });

  it('should report nothing for an empty window rather than claiming a percentage', () => {
    expect(periodSteps({ originalPeriodEnd: 100, originalPeriodStart: 100, period: [100, 100] }))
      .toBeUndefined();
  });

  it('should report nothing for a window that ends before it starts', () => {
    expect(periodSteps({ originalPeriodEnd: 50, originalPeriodStart: 100, period: [100, 100] }))
      .toBeUndefined();
  });

  it('should clamp a cursor that has run past the window', () => {
    expect(periodSteps({ originalPeriodEnd: 200, originalPeriodStart: 100, period: [100, 999] }))
      .toStrictEqual({ current: 100, total: 100 });
  });

  it('should clamp a cursor that sits before the window', () => {
    expect(periodSteps({ originalPeriodEnd: 200, originalPeriodStart: 100, period: [100, 40] }))
      .toStrictEqual({ current: 0, total: 100 });
  });
});
