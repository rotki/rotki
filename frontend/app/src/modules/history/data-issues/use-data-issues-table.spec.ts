import type { Filters } from '@/modules/history/data-issues/data-issue-filter-keys';
import { get, set } from '@vueuse/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComputedRef, ref, type Ref } from 'vue';
import { DEFAULT_LIST_STATES } from '@/modules/history/data-issues/constants';
import { isManualOnlyFilter } from '@/modules/history/data-issues/data-issues-panel-utils';
import { useDataIssuesTable } from '@/modules/history/data-issues/use-data-issues-table';

interface CapturedTableOptions {
  filters?: Ref<Filters>;
  params?: Array<{ values: ComputedRef<Record<string, unknown>> }>;
}

const captured: CapturedTableOptions = {};

vi.mock('@/modules/core/table/use-server-table', () => ({
  routeWhen: (): { mode: 'route' } => ({ mode: 'route' }),
  useServerTable: (options: CapturedTableOptions): Record<string, unknown> => {
    captured.filters = options.filters;
    captured.params = options.params;
    const filter = options.filters ?? ref<Filters>({});
    return {
      collection: ref({ data: [], found: 0, limit: 10, total: 0 }),
      error: ref(undefined),
      filter,
      isLoading: ref(false),
      pagination: ref({}),
      refetch: vi.fn(),
      setFilter: (next: Filters): void => {
        set(filter, next);
      },
    };
  },
}));

vi.mock('@/modules/history/data-issues/use-data-issues', () => ({
  useDataIssues: (): Record<string, unknown> => ({
    fetchData: vi.fn(),
    fetchIssue: vi.fn(),
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issue-fields', () => ({
  useDataIssueFields: (): unknown[] => [],
}));

describe('useDataIssuesTable manualOnly handling', () => {
  beforeEach(() => {
    captured.filters = undefined;
    captured.params = undefined;
  });

  it('should treat boolean true and URL string "true" as confirmedActive and drop default open states', () => {
    const table = useDataIssuesTable(true);
    const defaultParam = captured.params?.[0]?.values;

    expect(get(table.confirmedActive)).toBe(false);
    expect(get(defaultParam)).toStrictEqual({ state: [...DEFAULT_LIST_STATES] });

    set(captured.filters!, { manualOnly: 'true' });
    expect(get(table.confirmedActive)).toBe(true);
    expect(get(defaultParam)).toStrictEqual({});

    set(captured.filters!, { manualOnly: true });
    expect(get(table.confirmedActive)).toBe(true);
    expect(get(defaultParam)).toStrictEqual({});
  });

  it('should treat string "false" and undefined as inactive and keep default open states', () => {
    const table = useDataIssuesTable(true);
    const defaultParam = captured.params?.[0]?.values;

    set(captured.filters!, { manualOnly: 'false' });
    expect(get(table.confirmedActive)).toBe(false);
    expect(get(defaultParam)).toStrictEqual({ state: [...DEFAULT_LIST_STATES] });

    expect(isManualOnlyFilter('false')).toBe(false);
    expect(isManualOnlyFilter(undefined)).toBe(false);
  });
});
