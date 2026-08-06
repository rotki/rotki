import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import DataIssuesTable from '@/modules/history/data-issues/components/DataIssuesTable.vue';
import DataIssuesView from '@/modules/history/data-issues/DataIssuesView.vue';
import NoDataScreen from '@/modules/shell/components/NoDataScreen.vue';

// Shared, per-test-mutable state backing the mocked composables. Plain values set
// before each mount; the factories snapshot them into refs when the view mounts.
interface MockState {
  baselineTotal: number;
  filters: Record<string, unknown>;
  isLoading: boolean;
  rows: DataIssue[];
}

const state = vi.hoisted((): MockState => ({
  baselineTotal: 0,
  filters: {},
  isLoading: false,
  rows: [],
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  routeWhen: (): { mode: 'route' } => ({ mode: 'route' }),
  useServerTable: (): Record<string, unknown> => ({
    collection: ref({ data: state.rows, found: state.rows.length, limit: 10, total: state.rows.length }),
    filter: ref(state.filters),
    isLoading: ref(state.isLoading),
    matchers: ref([]),
    pagination: ref({}),
    refetch: vi.fn().mockResolvedValue(undefined),
    setFilter: vi.fn(),
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues', () => ({
  useDataIssues: (): Record<string, unknown> => ({
    dismiss: vi.fn(),
    fetchData: vi.fn(),
    resolveManually: vi.fn(),
    retry: vi.fn(),
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-summary', () => ({
  useDataIssuesSummary: (): Record<string, unknown> => ({
    actionableCount: ref(0),
    baselineTotal: ref(state.baselineTotal),
    counts: ref({}),
    dismissInlinePanels: vi.fn(),
    refreshSummary: vi.fn().mockResolvedValue(undefined),
  }),
}));

async function createWrapper(): Promise<VueWrapper<InstanceType<typeof DataIssuesView>>> {
  const wrapper = mount(DataIssuesView, {
    global: {
      plugins: [createPinia()],
      stubs: {
        DataIssueDetailDrawer: true,
        DataIssuesTable: true,
        DataIssueSummaryBar: true,
        NoDataScreen: true,
        PillFilterBar: true,
        ResolveManuallyDialog: true,
        TablePageLayout: { template: '<div><slot /></div>' },
      },
    },
    props: {
      mainPage: true,
    },
  });
  await flushPromises();
  return wrapper;
}

describe('data-issues view empty states', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    state.baselineTotal = 0;
    state.filters = {};
    state.isLoading = false;
    state.rows = [];
  });

  it('should show the reassuring all-clear screen when no issues exist at all', async () => {
    state.baselineTotal = 0;
    const wrapper = await createWrapper();

    expect(wrapper.findComponent(NoDataScreen).exists()).toBe(true);
    expect(wrapper.findComponent(DataIssuesTable).exists()).toBe(false);
  });

  it('should keep the all-clear screen (not flash the table) while an empty inbox is refreshing', async () => {
    state.baselineTotal = 0;
    state.isLoading = true;
    const wrapper = await createWrapper();

    expect(wrapper.findComponent(NoDataScreen).exists()).toBe(true);
    expect(wrapper.findComponent(DataIssuesTable).exists()).toBe(false);
  });

  it('should show the table (not the all-clear screen) once any issue exists', async () => {
    state.baselineTotal = 4;
    const wrapper = await createWrapper();

    expect(wrapper.findComponent(NoDataScreen).exists()).toBe(false);
    expect(wrapper.findComponent(DataIssuesTable).exists()).toBe(true);
  });

  it('should use the "no match" empty copy when filters are active but the list is empty', async () => {
    state.baselineTotal = 4;
    state.rows = [];
    state.filters = { state: ['open'] };
    const wrapper = await createWrapper();

    const table = wrapper.findComponent(DataIssuesTable);
    expect(table.props('emptyDescription')).toBe('data_issues.empty.filtered');
    expect(table.props('showClearFilters')).toBe(true);
  });

  it('should use the "none" empty copy when there are no active filters', async () => {
    state.baselineTotal = 4;
    state.rows = [];
    state.filters = {};
    const wrapper = await createWrapper();

    const table = wrapper.findComponent(DataIssuesTable);
    expect(table.props('emptyDescription')).toBe('data_issues.empty.none');
    expect(table.props('showClearFilters')).toBe(false);
  });
});
