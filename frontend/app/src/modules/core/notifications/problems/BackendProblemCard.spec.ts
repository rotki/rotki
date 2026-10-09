import { mockT } from '@test/i18n';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it } from 'vitest';
import { type BackendProblem, foldReport, type ProblemMessage, type ProblemReport } from '@/modules/core/notifications/problems/backend-problem-tree';
import BackendProblemCard from '@/modules/core/notifications/problems/BackendProblemCard.vue';

const AT = new Date('2026-10-21T10:00:00Z');

function badData(record: string): ProblemMessage {
  return {
    fields: { error: 'Missing key', record },
    group: ['error', 'bad_data', 'kucoin', record],
    key: 'bad_data',
    subject: 'kucoin',
    value: `could not read a ${record}`,
    verbosity: 'error',
  };
}

function report(source: ProblemMessage, count = 1): ProblemReport {
  return { at: AT, count, identity: JSON.stringify(source.group), source };
}

function problemOf(...reports: ProblemReport[]): BackendProblem {
  const [problem] = reports.reduce<BackendProblem[]>((problems, next) => foldReport(problems, next), []);
  return problem;
}

function summaryOf(problems: number, seen: number): string {
  return mockT('backend_problems.summary', {
    problems: mockT('backend_problems.count', { count: problems }),
    seen: mockT('backend_problems.seen', { count: seen }),
  });
}

function countText(problem: BackendProblem): string {
  const wrapper: VueWrapper = mount(BackendProblemCard, {
    global: { stubs: { BackendProblemItem: true, TimeAgoDisplay: true } },
    props: { problem },
  });
  return wrapper.find('[data-testid=backend-problem-count]').text();
}

describe('modules/core/notifications/problems/BackendProblemCard', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should count the problems and the sends apart, so a single send reads as seen once', () => {
    expect(countText(problemOf(report(badData('balance'))))).toBe(summaryOf(1, 1));
  });

  it('should count every send, held repeats included, in the seen part', () => {
    expect(countText(problemOf(report(badData('balance'), 5), report(badData('trade'))))).toBe(summaryOf(2, 6));
  });
});
