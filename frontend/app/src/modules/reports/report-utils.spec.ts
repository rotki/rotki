import { describe, expect, it } from 'vitest';
import { stoppedAtPlanLimit } from '@/modules/reports/report-utils';

describe('modules/reports/report-utils', () => {
  describe('stoppedAtPlanLimit', () => {
    it('should be true when processing stopped at the limit with actions left over', () => {
      expect(stoppedAtPlanLimit({ processedActions: 1000, totalActions: 3000 }, 1000)).toBe(true);
    });

    it('should be true when the last batch carried processing past the limit', () => {
      expect(stoppedAtPlanLimit({ processedActions: 1003, totalActions: 3000 }, 1000)).toBe(true);
    });

    it('should be false when every action was processed', () => {
      expect(stoppedAtPlanLimit({ processedActions: 1000, totalActions: 1000 }, 1000)).toBe(false);
    });

    it('should be false when actions were skipped before reaching the limit', () => {
      expect(stoppedAtPlanLimit({ processedActions: 400, totalActions: 450 }, 1000)).toBe(false);
    });

    it('should be false when the plan has no limit', () => {
      expect(stoppedAtPlanLimit({ processedActions: 1000, totalActions: 3000 }, -1)).toBe(false);
    });
  });
});
