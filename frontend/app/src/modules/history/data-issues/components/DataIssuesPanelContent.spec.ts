import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { computed, type Ref, ref } from 'vue';
import DataIssuePanelCard from '@/modules/history/data-issues/components/DataIssuePanelCard.vue';
import DataIssuesPanelContent from '@/modules/history/data-issues/components/DataIssuesPanelContent.vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';

interface MockState {
  hasActiveSelection: boolean;
  issues: DataIssue[];
  loading: boolean;
}

const state = vi.hoisted((): MockState => ({
  hasActiveSelection: false,
  issues: [],
  loading: false,
}));

const clearSelection = vi.hoisted(() => vi.fn().mockResolvedValue(undefined));
const refreshList = vi.hoisted(() => vi.fn().mockResolvedValue(undefined));
const reloadAll = vi.hoisted(() => vi.fn().mockResolvedValue(undefined));

vi.mock('@/modules/history/data-issues/use-data-issues-panel-list', () => ({
  useDataIssuesPanelList: (): Record<string, unknown> => ({
    hasRemediatingRows: computed(() => false),
    isEmpty: computed(() => state.issues.length === 0),
    loading: computed(() => state.loading),
    loadingMore: computed(() => false),
    loadMore: vi.fn().mockResolvedValue(undefined),
    refreshList,
    reloadAll,
    rows: computed(() => state.issues.map(issue => ({
      description: { amounts: {}, messageKey: 'k', shortMessageKey: 'k' },
      eventRoute: undefined,
      issue,
    }))),
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-panel-selection', () => ({
  useDataIssuesPanelSelection: (): Record<string, unknown> => ({
    activeEventIdentifier: computed(() => undefined),
    clearSelection,
    goToEvent: vi.fn().mockResolvedValue(undefined),
    hasActiveSelection: computed(() => state.hasActiveSelection),
    isActiveRow: (): boolean => false,
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-panel-polling', () => ({
  useDataIssuesPanelPolling: vi.fn(),
}));

interface Actions {
  modelDrawerOpen?: Ref<boolean>;
  modelSelectedIssue?: Ref<DataIssue | undefined>;
  onResolveRequest: Mock;
}

/** Filled in when the component mounts, so a test can drive the detail-action refs. */
const actions = vi.hoisted((): Actions => ({ onResolveRequest: vi.fn() }));

function mounted<T>(value: T | undefined): T {
  if (value === undefined)
    throw new Error('the component has not been mounted yet');
  return value;
}

vi.mock('@/modules/history/data-issues/use-data-issue-detail-actions', () => ({
  useDataIssueDetailActions: (): Record<string, unknown> => {
    actions.modelDrawerOpen = ref<boolean>(false);
    actions.modelSelectedIssue = ref<DataIssue>();
    return {
      modelActionBusy: ref(false),
      modelDrawerOpen: actions.modelDrawerOpen,
      modelResolveOpen: ref(false),
      modelSelectedIssue: actions.modelSelectedIssue,
      onDismiss: vi.fn(),
      onResolveConfirm: vi.fn(),
      onResolveRequest: actions.onResolveRequest,
      onRetry: vi.fn(),
      openDetail: vi.fn(),
    };
  },
}));

vi.mock('@/modules/history/data-issues/use-data-issue-fields', () => ({
  useDataIssueFields: (): unknown[] => [],
}));

function createIssue(id: number): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: null,
    id,
    kind: IssueKind.NEGATIVE_BALANCE,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    tsEnd: 1710000000,
    tsStart: 1710000000,
  };
}

async function createWrapper(): Promise<VueWrapper<InstanceType<typeof DataIssuesPanelContent>>> {
  const wrapper = mount(DataIssuesPanelContent, {
    global: {
      plugins: [createPinia()],
      stubs: {
        DataIssueDetailContent: true,
        DataIssuePanelCard: true,
        PillFilterBar: true,
        PinnedDetailSheet: true,
        ResolveManuallyDialog: true,
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe('dataIssuesPanelContent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    state.hasActiveSelection = false;
    state.issues = [];
    state.loading = false;
  });

  it('should load the list and the summary on mount', async () => {
    await createWrapper();

    expect(reloadAll).toHaveBeenCalledOnce();
  });

  it('should show the all-clear shield when the inbox is empty and unfiltered', async () => {
    const wrapper = await createWrapper();

    expect(wrapper.text()).toContain('data_issues.empty.all_clear_title');
    expect(wrapper.find('[data-testid=data-issues-panel-list]').exists()).toBe(false);
  });

  it('should show a spinner instead of the shield while the first load runs', async () => {
    state.loading = true;
    const wrapper = await createWrapper();

    expect(wrapper.text()).not.toContain('data_issues.empty.all_clear_title');
  });

  it('should hand each rendered card its issue, the virtualised count reflecting the window rather than the data', async () => {
    state.issues = [createIssue(1), createIssue(2), createIssue(3)];
    const wrapper = await createWrapper();

    expect(wrapper.find('[data-testid=data-issues-panel-list]').exists()).toBe(true);
    const cards = wrapper.findAllComponents(DataIssuePanelCard);
    expect(cards.length).toBeGreaterThan(0);
    expect(cards.map(card => card.props('issue').id)).toStrictEqual(
      state.issues.slice(0, cards.length).map(issue => issue.id),
    );
  });

  it('should not show the all-clear shield once issues exist', async () => {
    state.issues = [createIssue(1)];
    const wrapper = await createWrapper();

    expect(wrapper.text()).not.toContain('data_issues.empty.all_clear_title');
  });

  it('should hide the selection bar when no event is highlighted', async () => {
    const wrapper = await createWrapper();

    expect(wrapper.find('[data-testid=data-issues-panel-active-selection]').exists()).toBe(false);
  });

  it('should show the selection bar while an event is highlighted', async () => {
    state.hasActiveSelection = true;
    const wrapper = await createWrapper();

    expect(wrapper.find('[data-testid=data-issues-panel-active-selection]').exists()).toBe(true);
  });

  it('should clear the highlight from the selection bar', async () => {
    state.hasActiveSelection = true;
    const wrapper = await createWrapper();

    await wrapper.find('[data-testid=data-issues-panel-clear-selection]').trigger('click');

    expect(clearSelection).toHaveBeenCalledOnce();
  });

  it('should select the issue before opening the resolve dialog from a card', async () => {
    state.issues = [createIssue(7)];
    const wrapper = await createWrapper();

    await wrapper.findComponent(DataIssuePanelCard).vm.$emit('resolve', createIssue(7));

    expect(get(mounted(actions.modelSelectedIssue))?.id).toBe(7);
    expect(actions.onResolveRequest).toHaveBeenCalledOnce();
  });

  it('should tell the host drawer when a stacked overlay opens', async () => {
    const wrapper = await createWrapper();
    expect(wrapper.props('subDialogOpen')).toBe(false);

    set(mounted(actions.modelDrawerOpen), true);
    await flushPromises();

    expect(wrapper.emitted('update:subDialogOpen')?.at(-1)).toStrictEqual([true]);
  });

  it('should reload the list when the filters settle', async () => {
    const wrapper = await createWrapper();
    refreshList.mockClear();

    wrapper.findComponent({ name: 'PillFilterBar' }).vm.$emit('update:matches', { asset: 'ETH' });
    await vi.waitFor(() => {
      expect(refreshList).toHaveBeenCalledOnce();
    });
  });

  it('should emit close when the view-all link is used', async () => {
    const wrapper = await createWrapper();

    await wrapper.find('[data-testid=data-issues-panel-view-all]').trigger('click');

    expect(wrapper.emitted('close')).toHaveLength(1);
  });
});
