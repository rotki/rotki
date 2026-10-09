import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Router, useRouter } from 'vue-router';
import { useReportIssue } from '@/modules/core/common/use-report-issue';
import { foldReport, type ProblemMessage } from '@/modules/core/notifications/problems/backend-problem-tree';
import { useBackendProblemActions } from '@/modules/core/notifications/problems/use-backend-problem-actions';

const { showReportIssue } = vi.hoisted(() => ({ showReportIssue: vi.fn() }));

vi.mock('@/modules/core/common/use-report-issue', () => ({
  useReportIssue: vi.fn(() => ({ show: showReportIssue })),
}));

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): { getLocationData: () => undefined } => ({ getLocationData: () => undefined }),
}));

function actionFor(source: ProblemMessage): ReturnType<ReturnType<typeof useBackendProblemActions>['itemAction']> {
  const [problem] = foldReport([], { at: new Date('2026-09-30T07:00:00Z'), count: 1, identity: 'identity', source });
  return useBackendProblemActions().itemAction(problem, problem.items[0]);
}

const push = vi.fn<Router['push']>(async () => undefined);

describe('useBackendProblemActions', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue(createMock<Router>({ push }));
  });

  describe('a missing price', () => {
    it('should open the historic price dialog for the asset at the time it was missing', () => {
      actionFor({ fields: { asset: 'ETH', timestamp: 1700000000 }, group: [], key: 'price', subject: null, value: 'v', verbosity: 'warning' })?.run();

      expect(push).toHaveBeenCalledWith({
        name: '/price-manager/historic/',
        query: { add: 'true', fromAsset: 'ETH', timestamp: '1700000000' },
      });
    });

    it('should open the latest price dialog for a missing current price', () => {
      actionFor({ fields: { asset: 'ETH', timestamp: null }, group: [], key: 'price', subject: null, value: 'v', verbosity: 'warning' })?.run();

      expect(push).toHaveBeenCalledWith({
        name: '/price-manager/latest/',
        query: { add: 'true', fromAsset: 'ETH' },
      });
    });

    it('should offer nothing for a batch that names no asset', () => {
      expect(actionFor({ fields: { asset: null, timestamp: null }, group: [], key: 'price', subject: null, value: 'v', verbosity: 'warning' })).toBeUndefined();
    });
  });

  it.each([
    { fields: { error: 'Missing key', record: 'trade' }, group: [], key: 'bad_data', subject: null, value: 'Could not read a trade', verbosity: 'error' },
    { fields: { entry: 'tag' }, group: [], key: 'local_db', subject: null, value: 'Could not read a tag', verbosity: 'error' },
    { fields: { operation: 'data_migration' }, group: [], key: 'internal', subject: null, value: 'A migration failed', verbosity: 'error' },
  ] satisfies ProblemMessage[])('should offer to report a $key problem, carrying its details', (source) => {
    actionFor(source)?.run();

    expect(useReportIssue).toHaveBeenCalled();
    expect(showReportIssue).toHaveBeenCalledWith(expect.objectContaining({
      description: expect.stringContaining(source.value),
      title: `backend_problems.title.${source.key}`,
    }));
  });

  it.each([
    { fields: { error: 'HTTP 502', record: 'trade' }, group: [], key: 'network', subject: null, value: 'v', verbosity: 'error' },
    { fields: { feature: 'multi_trade' }, group: [], key: 'unsupported', subject: null, value: 'v', verbosity: 'warning' },
    { fields: { identifier: '1234' }, group: [], key: 'unknown_asset', subject: null, value: 'v', verbosity: 'warning' },
  ] satisfies ProblemMessage[])('should offer nothing for a $key problem', (source) => {
    expect(actionFor(source)).toBeUndefined();
  });
});
