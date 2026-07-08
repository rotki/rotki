import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import DataIssueDetailDrawer from '@/modules/history/data-issues/components/DataIssueDetailDrawer.vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { createRuiPlugin } from '@/plugins/rui';

const push = vi.fn();

// Override the global vue-router mock with a stable `push` spy so the navigation
// away from a related event can be asserted.
vi.mock('vue-router', () => ({
  useRouter: (): Record<string, unknown> => ({ push }),
}));

// Render the drawer's default slot inline so its content lands in the wrapper DOM
// instead of a teleport target.
const DrawerStub = defineComponent({
  props: { modelValue: { default: false, type: Boolean } },
  setup(_, { slots }): () => VNode {
    return () => h('div', slots.default?.());
  },
});

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: 'grp-1',
    id: 1,
    kind: IssueKind.NEGATIVE_BALANCE,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {
      derivedBalanceBeforeEvent: '5',
      eventIdentifier: 123,
      inMemoryNegativeAmount: '-2',
    },
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    tsEnd: 1710000000,
    tsStart: 1710000000,
    ...overrides,
  };
}

function createWrapper(issue?: DataIssue): VueWrapper<InstanceType<typeof DataIssueDetailDrawer>> {
  return mount(DataIssueDetailDrawer, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        AssetDetails: true,
        CounterpartyDisplay: true,
        DataIssueDescription: true,
        DataIssueDetectedTime: true,
        DataIssueKindChip: true,
        DataIssueRemediationTimeline: true,
        DataIssueStateChip: true,
        HistoryEventAccount: true,
        LocationDisplay: true,
        RuiNavigationDrawer: DrawerStub,
      },
    },
    props: {
      issue,
      modelValue: true,
    },
  });
}

describe('dataIssueDetailDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render a related-event link for an issue that carries an event identifier', () => {
    const wrapper = createWrapper(createIssue());

    expect(wrapper.find('[data-testid="data-issue-related-event"]').exists()).toBe(true);
  });

  it('should not render a related-event link when the payload has no event identifier', () => {
    const wrapper = createWrapper(createIssue({ kind: IssueKind.CURRENT_BALANCE_MISMATCH, payload: {} }));

    expect(wrapper.find('[data-testid="data-issue-related-event"]').exists()).toBe(false);
  });

  it('should close the drawer and navigate to the related event on click', async () => {
    const wrapper = createWrapper(createIssue());

    await wrapper.find('[data-testid="data-issue-related-event"]').trigger('click');

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toStrictEqual([false]);
    expect(push).toHaveBeenCalledWith(expect.objectContaining({
      query: expect.objectContaining({
        highlightedNegativeBalanceEvent: '123',
        targetGroupIdentifier: 'grp-1',
      }),
    }));
  });

  it('should show the resolution note when the payload carries a string note', () => {
    const wrapper = createWrapper(createIssue({
      payload: { resolution: { note: 'fixed by hand' } },
      state: IssueState.RESOLVED,
    }));

    expect(wrapper.text()).toContain('fixed by hand');
  });

  it('should ignore a non-string resolution note', () => {
    const wrapper = createWrapper(createIssue({
      payload: { resolution: { note: 42 } },
      state: IssueState.RESOLVED,
    }));

    expect(wrapper.text()).not.toContain('data_issues.detail.resolution_note');
  });

  it('should not render a resolution note section when there is no resolution', () => {
    const wrapper = createWrapper(createIssue({ payload: {}, state: IssueState.OPEN }));

    expect(wrapper.text()).not.toContain('data_issues.detail.resolution_note');
  });

  it('should emit the action events with the issue id from the footer buttons', async () => {
    const wrapper = createWrapper(createIssue({ id: 8 }));

    await wrapper.find('[data-testid="data-issue-detail-dismiss"]').trigger('click');
    await wrapper.find('[data-testid="data-issue-detail-resolve"]').trigger('click');

    expect(wrapper.emitted('dismiss')?.[0]).toStrictEqual([8]);
    expect(wrapper.emitted('resolve')?.[0]).toStrictEqual([8]);
  });
});
