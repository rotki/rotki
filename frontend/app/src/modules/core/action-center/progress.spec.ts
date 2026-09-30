import { describe, expect, it } from 'vitest';
import { progressSince, snapshotCounts } from './progress';

function row(id: string, count: number, loading = false): { id: string; count: number; loading: boolean } {
  return { count, id, loading };
}

describe('modules/core/action-center/progress', () => {
  describe('snapshotCounts', () => {
    it('should remember every row with something pending, and leave out the rest', () => {
      expect(snapshotCounts([row('duplicates', 40), row('prices', 0), row('mappings', 3)])).toEqual({ duplicates: 40, mappings: 3 });
    });
  });

  describe('progressSince', () => {
    it('should report what a row had at the snapshot once it is lower', () => {
      expect(progressSince({ duplicates: 40 }, [row('duplicates', 12)])).toEqual({ duplicates: 40 });
    });

    it('should report a row that cleared completely', () => {
      expect(progressSince({ conflicts: 2 }, [row('conflicts', 0)])).toEqual({ conflicts: 2 });
    });

    it('should leave out a row that is unchanged or grew, since growth is what "new" marks', () => {
      expect(progressSince({ duplicates: 40, prices: 3 }, [row('duplicates', 40), row('prices', 7)])).toEqual({});
    });

    it('should leave out a row that was not pending at the snapshot', () => {
      expect(progressSince({}, [row('duplicates', 0), row('prices', 5)])).toEqual({});
    });

    it('should leave out a row that is re-reading, whose count is not an answer yet', () => {
      expect(progressSince({ duplicates: 40 }, [row('duplicates', 0, true)])).toEqual({});
    });
  });
});
