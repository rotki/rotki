import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import DataIssuesTable from '@/modules/history/data-issues/components/DataIssuesTable.vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import { createRuiPlugin } from '@/plugins/rui';

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: null,
    id: 1,
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
    ...overrides,
  };
}

function createWrapper(rows: DataIssue[]): VueWrapper<InstanceType<typeof DataIssuesTable>> {
  return mount(DataIssuesTable, {
    global: {
      plugins: [createPinia(), createRuiPlugin({})],
      stubs: {
        AssetDetails: true,
        CounterpartyDisplay: true,
        DataIssueKindChip: true,
        DataIssueStateChip: true,
        DateDisplay: true,
        HistoryEventAccount: true,
        LocationDisplay: true,
      },
    },
    props: {
      emptyDescription: 'empty',
      rows,
    },
  });
}

describe('data-issues table', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should render the protocol column between account and state', () => {
    const headers = createWrapper([]).findAll('thead th').map(th => th.text());
    const account = headers.indexOf('common.account');
    const protocol = headers.indexOf('data_issues.headers.protocol');
    const state = headers.indexOf('data_issues.headers.state');

    expect(protocol).toBeGreaterThan(account);
    expect(state).toBeGreaterThan(protocol);
  });

  it('should render a counterparty for a row that has a protocol', () => {
    const wrapper = createWrapper([createIssue({ id: 1, protocol: 'uniswap-v3' })]);
    const counterparty = wrapper.findComponent(CounterpartyDisplay);

    expect(counterparty.exists()).toBe(true);
    expect(counterparty.props('counterparty')).toBe('uniswap-v3');
  });

  it('should render a dash instead of a counterparty when the protocol is null', () => {
    const wrapper = createWrapper([createIssue({ id: 1, protocol: null })]);

    expect(wrapper.findComponent(CounterpartyDisplay).exists()).toBe(false);
  });

  it('should forward a row quick dismiss action', async () => {
    const issue = createIssue({ id: 5, state: IssueState.OPEN });
    const wrapper = createWrapper([issue]);

    await wrapper.find('[data-testid="data-issues-panel-dismiss"]').trigger('click');

    expect(wrapper.emitted('dismiss')?.[0]?.[0]).toStrictEqual(issue);
  });

  it('should emit open when the row action button is clicked', async () => {
    const issue = createIssue({ id: 7 });
    const wrapper = createWrapper([issue]);

    await wrapper.find('[data-testid="data-issues-view-details"]').trigger('click');

    expect(wrapper.emitted('open')?.[0]?.[0]).toStrictEqual(issue);
  });

  it('should emit open with the row when a row is clicked', async () => {
    // A lightweight table stub whose button re-emits `click:row`, so we assert the
    // component forwards it as `open` without depending on RuiDataTable internals.
    const RuiDataTableStub = defineComponent({
      emits: ['click:row'],
      props: { rows: { default: () => [], type: Array } },
      setup(props, { emit }): () => VNode {
        return () => h('button', { onClick: () => emit('click:row', props.rows[0]) });
      },
    });
    const issue = createIssue({ id: 42 });
    const wrapper = mount(DataIssuesTable, {
      global: {
        plugins: [createPinia()],
        stubs: {
          CounterpartyDisplay: true,
          RuiDataTable: RuiDataTableStub,
        },
      },
      props: {
        emptyDescription: 'empty',
        rows: [issue],
      },
    });

    await wrapper.find('button').trigger('click');

    expect(wrapper.emitted('open')?.[0]?.[0]).toStrictEqual(issue);
  });
});
