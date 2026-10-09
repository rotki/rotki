import { describe, expect, it } from 'vitest';
import {
  type BackendProblem,
  foldReport,
  MAX_ITEMS_PER_PROBLEM,
  type ProblemMessage,
  type ProblemReport,
} from '@/modules/core/notifications/problems/backend-problem-tree';

const EARLY = new Date('2026-09-30T07:00:00Z');
const LATE = new Date('2026-09-30T10:00:00Z');

function badData(record: string, value = `could not read a ${record}`, subject: string | null = 'kucoin'): ProblemMessage {
  return {
    fields: { error: 'Missing key', record },
    group: ['error', 'bad_data', subject, record],
    key: 'bad_data',
    subject,
    value,
    verbosity: 'error',
  };
}

function report(source: ProblemMessage, at: Date = EARLY, count = 1): ProblemReport {
  return { at, count, identity: JSON.stringify(source.group), source };
}

function fold(...reports: ProblemReport[]): BackendProblem[] {
  return reports.reduce<BackendProblem[]>((problems, next) => foldReport(problems, next), []);
}

describe('foldReport', () => {
  it('should open a parent per verbosity, family and location', () => {
    const problems = fold(
      report(badData('balance')),
      report(badData('balance', 'x', 'binance')),
      report({ ...badData('balance'), group: ['warning', 'bad_data', 'kucoin', 'balance'], verbosity: 'warning' }),
    );

    expect(problems).toHaveLength(3);
  });

  it('should file distinct identities as items of one parent', () => {
    const [problem] = fold(report(badData('balance')), report(badData('trade')));

    expect(problem.items.map(({ identity }) => identity)).toHaveLength(2);
    expect(problem).toMatchObject({ itemTotal: 2, repeats: 2 });
  });

  it('should fold a repeat into its item and count every send it stands for', () => {
    const [problem] = fold(report(badData('balance')), report(badData('balance'), LATE, 3));

    expect(problem.items).toMatchObject([{ firstSeen: EARLY, lastSeen: LATE, repeats: 4 }]);
    expect(problem).toMatchObject({ itemTotal: 1, repeats: 4 });
  });

  it('should keep the newer sentence when a held repeat is older than the item', () => {
    const [problem] = fold(
      report(badData('balance', 'newer'), LATE),
      report(badData('balance', 'older'), EARLY),
    );

    expect(problem.items[0]).toMatchObject({ firstSeen: EARLY, lastSeen: LATE, source: { value: 'newer' } });
  });

  it('should list the newest parent first', () => {
    const problems = fold(
      report(badData('balance', 'x', 'kraken'), LATE),
      report(badData('balance', 'x', 'binance'), EARLY),
    );

    expect(problems.map(({ subject }) => subject)).toEqual(['kraken', 'binance']);
  });

  it('should keep at most the newest items and count the ones it dropped', () => {
    const reports = Array.from({ length: MAX_ITEMS_PER_PROBLEM + 3 }, (_, index) =>
      report(badData(`record-${index}`), new Date(EARLY.getTime() + index * 1000)));

    const [problem] = fold(...reports);

    expect(problem.items).toHaveLength(MAX_ITEMS_PER_PROBLEM);
    expect(problem.itemTotal).toBe(MAX_ITEMS_PER_PROBLEM + 3);
    expect(problem.items[0].source.value).toBe(`could not read a record-${MAX_ITEMS_PER_PROBLEM + 2}`);
  });

  describe('read state', () => {
    function readProblem(): BackendProblem[] {
      return fold(report(badData('balance'))).map(problem => ({ ...problem, read: true }));
    }

    it('should mark a parent unread when a new item arrives', () => {
      const [problem] = foldReport(readProblem(), report(badData('trade')));

      expect(problem.read).toBe(false);
    });

    it('should leave a parent read when a known item repeats', () => {
      const [problem] = foldReport(readProblem(), report(badData('balance'), LATE));

      expect(problem.read).toBe(true);
    });
  });
});
