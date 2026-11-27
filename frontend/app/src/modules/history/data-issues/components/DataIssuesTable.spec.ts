import type { SpamAssessment } from '@/modules/assets/spam/use-spam-assessments';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import SpamAssessmentHint from '@/modules/assets/spam/SpamAssessmentHint.vue';
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

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
});

function createWrapper(
  rows: DataIssue[],
  spamAssessments?: Record<string, SpamAssessment>,
  spamUnavailable = false,
): VueWrapper<InstanceType<typeof DataIssuesTable>> {
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
        RuiMenu,
        SpamAssessmentHint: true,
      },
    },
    props: {
      emptyDescription: 'empty',
      pagination: { limit: 10, page: 1, total: rows.length },
      rows,
      spamAssessments,
      spamUnavailable,
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

  it('should ask beside a row quick dismiss and forward nothing until confirmed', async () => {
    const wrapper = createWrapper([createIssue({ id: 5, state: IssueState.OPEN })]);

    await wrapper.find('[data-testid="data-issues-panel-dismiss"]').trigger('click');

    expect(wrapper.find('[data-testid="inline-confirm"]').text()).toContain('data_issues.action.dismiss.confirm.message');
    expect(wrapper.emitted('dismiss')).toBeUndefined();
    expect(wrapper.emitted('open')).toBeUndefined();
  });

  it('should forward a row quick dismiss once confirmed', async () => {
    const issue = createIssue({ id: 5, state: IssueState.OPEN });
    const wrapper = createWrapper([issue]);

    await wrapper.find('[data-testid="data-issues-panel-dismiss"]').trigger('click');
    await wrapper.find('[data-testid="inline-confirm-accept"]').trigger('click');

    expect(wrapper.emitted('dismiss')?.[0]?.[0]).toStrictEqual(issue);
  });

  it('should not render a separate spam estimate column', () => {
    const headers = createWrapper([]).findAll('thead th').map(th => th.text());

    expect(headers).not.toContain('spam_estimate.label');
  });

  it('should render an inline standalone quiet spam badge only for flagged ready assessments', () => {
    const flaggedToken = 'eip155:1/erc20:0x1111111111111111111111111111111111111111';
    const cleanToken = 'eip155:1/erc20:0x2222222222222222222222222222222222222222';
    const loadingToken = 'eip155:1/erc20:0x3333333333333333333333333333333333333333';
    const flagged: SpamAssessment = {
      prediction: {
        flagged: true,
        modelReasons: [],
        observedSignals: [],
        spamProbability: 0.9,
        threshold: 0.5,
      },
      status: 'ready',
    };
    const clean: SpamAssessment = {
      prediction: {
        flagged: false,
        modelReasons: [],
        observedSignals: [],
        spamProbability: 0.1,
        threshold: 0.5,
      },
      status: 'ready',
    };
    const wrapper = createWrapper(
      [
        createIssue({ asset: flaggedToken, id: 1 }),
        createIssue({ asset: cleanToken, id: 2 }),
        createIssue({ asset: loadingToken, id: 3 }),
        createIssue({ asset: 'ETH', id: 4 }),
        createIssue({ asset: null, id: 5 }),
      ],
      {
        [cleanToken]: clean,
        [flaggedToken]: flagged,
        [loadingToken]: { status: 'loading' },
      },
    );

    const hints = wrapper.findAllComponents(SpamAssessmentHint);
    expect(hints).toHaveLength(1);
    expect(hints[0].props('assessment')).toStrictEqual(flagged);
    expect(hints[0].props('standalone')).toBe(true);
    expect(hints[0].props('quiet')).toBe(true);
  });

  it('should show a calm unavailable notice when spam prediction is unavailable', () => {
    const hidden = createWrapper([], undefined, false);
    expect(hidden.find('[data-testid="data-issues-spam-unavailable"]').exists()).toBe(false);

    const shown = createWrapper([], undefined, true);
    expect(shown.get('[data-testid="data-issues-spam-unavailable"]').text()).toBe('spam_estimate.unavailable_notice');
  });

  it('should emit open when the row action button is clicked', async () => {
    const issue = createIssue({ id: 7 });
    const wrapper = createWrapper([issue]);

    await wrapper.find('[data-testid="data-issues-view-details"]').trigger('click');

    expect(wrapper.emitted('open')?.[0]?.[0]).toStrictEqual(issue);
  });
});
