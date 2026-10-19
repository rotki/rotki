import { describe, expect, it } from 'vitest';
import { decideCollapse } from '@/modules/core/table/table-selection-collapse';

describe('modules/core/table/table-selection-collapse', () => {
  describe('decideCollapse', () => {
    it('should stay expanded while the row fits', () => {
      expect(decideCollapse({ clientWidth: 600, collapsed: false, expandedWidth: 0, scrollWidth: 600 }))
        .toStrictEqual({ collapsed: false, expandedWidth: 0 });
    });

    it('should collapse once the row overflows, remembering the width it needed', () => {
      expect(decideCollapse({ clientWidth: 500, collapsed: false, expandedWidth: 0, scrollWidth: 640 }))
        .toStrictEqual({ collapsed: true, expandedWidth: 640 });
    });

    it('should stay collapsed until there is room for the whole row again', () => {
      expect(decideCollapse({ clientWidth: 639, collapsed: true, expandedWidth: 640, scrollWidth: 639 }))
        .toStrictEqual({ collapsed: true, expandedWidth: 640 });
    });

    it('should expand once the bar is as wide as the row needed', () => {
      expect(decideCollapse({ clientWidth: 640, collapsed: true, expandedWidth: 640, scrollWidth: 640 }))
        .toStrictEqual({ collapsed: false, expandedWidth: 640 });
    });
  });
});
