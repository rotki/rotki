import type { HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import type { DivergenceBoundaryEvent } from '@/modules/history/balances/use-balance-divergence';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { useDataIssueDivergence } from '@/modules/history/data-issues/use-data-issue-divergence';
import { createMock } from '@test/utils/create-mock';
import { mount } from '@vue/test-utils';
import { set } from '@vueuse/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DataIssueBalanceDivergence from './DataIssueBalanceDivergence.vue';

const { state, diagnostic, boundary } = await vi.hoisted(async () => {
  const { computed, ref } = await import('vue');
  const { get } = await import('@vueuse/core');
  const { HistoricalBalanceDivergenceEvent } = await import('@/modules/history/balances/types');
  const boundary: DivergenceBoundaryEvent = {
    color: 'warning',
    event: HistoricalBalanceDivergenceEvent.parse({
      blockNumber: 42,
      difference: '1',
      eventIdentifier: 123,
      groupIdentifier: 'group-1',
      onchainBalance: '3',
      timestamp: 1700000000,
      trackedBalance: '2',
      txHash: `0x${'1'.repeat(64)}`,
    }),
    key: 'first_diverged',
  };
  const state = {
    available: ref<boolean>(true),
    boundaries: ref<DivergenceBoundaryEvent[]>([]),
    canSearch: ref<boolean>(true),
    loading: ref<boolean>(false),
    missingArchive: ref<boolean>(false),
    status: ref<HistoricalBalanceDivergenceResponse['status']>(),
    summary: ref<string>(),
    summaryInFooter: ref<boolean>(false),
  };
  return {
    boundary,
    diagnostic: {
      available: computed<boolean>(() => get(state.available)),
      boundaries: computed<DivergenceBoundaryEvent[]>(() => get(state.boundaries)),
      canSearch: computed<boolean>(() => get(state.canSearch)),
      chain: computed<string | undefined>(() => 'eth'),
      chainName: computed<string>(() => 'Ethereum'),
      checkingArchive: ref<boolean>(false),
      error: ref<string>(),
      loading: computed<boolean>(() => get(state.loading)),
      missingArchive: computed<boolean>(() => get(state.missingArchive)),
      search: vi.fn<() => Promise<void>>(),
      status: computed<HistoricalBalanceDivergenceResponse['status'] | undefined>(() => get(state.status)),
      summary: computed<string | undefined>(() => get(state.summary)),
      summaryInFooter: computed<boolean>(() => get(state.summaryInFooter)),
      view: vi.fn<(boundary: DivergenceBoundaryEvent) => void>(),
    } satisfies ReturnType<typeof useDataIssueDivergence>,
    state,
  };
});

vi.mock('@/modules/history/data-issues/use-data-issue-divergence', () => ({
  useDataIssueDivergence: (): ReturnType<typeof useDataIssueDivergence> => diagnostic,
}));

function mountDiagnostic(busy = false): ReturnType<typeof mount> {
  return mount(DataIssueBalanceDivergence, {
    global: {
      stubs: {
        DateDisplay: { name: 'DateDisplay', props: { timestamp: Number, milliseconds: Boolean }, template: '<span>{{ timestamp }}</span>' },
        DivergenceComparison: {
          emits: ['view'],
          props: ['boundaries', 'asset', 'location'],
          template: '<div><button v-for="boundary in boundaries" :key="boundary.key" data-testid="test-divergence-boundary" @click="$emit(\'view\', boundary)">{{ boundary.event.eventIdentifier }}</button><p data-testid="test-divergence-footer"><slot name="footer" /></p></div>',
        },
        I18nT: { template: '<span><slot name="chain" /><slot name="link" /><slot name="date" /></span>' },
        InternalLink: { template: '<a><slot /></a>' },
        RuiAlert: { props: ['type', 'title', 'description'], template: '<div :data-type="type" :data-title="title">{{ description }}<slot /></div>' },
        RuiButton: { props: ['disabled', 'loading'], template: '<button :disabled="disabled" :data-loading="loading"><slot /></button>' },
        RuiIcon: true,
        RuiTooltip: { template: '<span><slot name="activator" /><slot /></span>' },
      },
    },
    props: {
      busy,
      issue: createMock<DataIssue>({ asset: 'ETH', tsEnd: 1710000000123 }),
    },
  });
}

describe('dataIssueBalanceDivergence detail-panel diagnostic', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(state.available, true);
    set(state.canSearch, true);
    set(state.loading, false);
    set(diagnostic.checkingArchive, false);
    set(state.missingArchive, false);
    set(state.boundaries, []);
    set(state.summary, undefined);
    set(state.summaryInFooter, false);
    set(state.status, undefined);
    set(diagnostic.error, undefined);
  });

  it('should state the issue time as the search bound and start diagnosis from the detail-panel action', async () => {
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="data-issue-divergence-scope"]').text()).toContain('1710000000123');
    expect(wrapper.findComponent({ name: 'DateDisplay' }).props('milliseconds')).toBe(true);
    await wrapper.get('[data-testid="data-issue-find-divergence"]').trigger('click');
    expect(diagnostic.search).toHaveBeenCalledOnce();
  });

  it('should close the containing detail panel and navigate to a returned event', async () => {
    set(state.boundaries, [boundary]);
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="test-divergence-boundary"]').text()).toBe('123');
    await wrapper.get('[data-testid="test-divergence-boundary"]').trigger('click');
    expect(wrapper.emitted('navigate')).toEqual([[]]);
    expect(diagnostic.view).toHaveBeenCalledWith(boundary);
  });

  it('should neither navigate nor close the detail panel for a boundary without a group', async () => {
    set(state.boundaries, [{ ...boundary, event: { ...boundary.event, groupIdentifier: null } }]);
    const wrapper = mountDiagnostic();
    await wrapper.get('[data-testid="test-divergence-boundary"]').trigger('click');
    expect(wrapper.emitted('navigate')).toBeUndefined();
    expect(diagnostic.view).not.toHaveBeenCalled();
  });

  it.each([
    [true, false, 'true'],
    [false, true, 'true'],
    [true, true, 'true'],
    [false, false, 'false'],
  ])('should bind search loading %s and archive checking %s to the button', (loading, checkingArchive, expected) => {
    set(state.loading, loading);
    set(diagnostic.checkingArchive, checkingArchive);
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="data-issue-find-divergence"]').attributes('data-loading')).toBe(expected);
  });

  it('should show a settings link and disable search when an archive node is missing', () => {
    set(state.missingArchive, true);
    set(state.canSearch, false);
    const wrapper = mountDiagnostic();
    const message = wrapper.get('[data-testid="data-issue-divergence-missing-archive"]').text();
    expect(message).toContain('Ethereum');
    expect(message).toContain('balance_divergence.settings_link');
    expect(wrapper.get('[data-testid="data-issue-find-divergence"]').attributes('disabled')).toBeDefined();
  });

  it('should disable search while an issue action is busy', () => {
    const wrapper = mountDiagnostic(true);
    expect(wrapper.get('[data-testid="data-issue-find-divergence"]').attributes('disabled')).toBeDefined();
  });

  it('should render the diagnosis summary including a no-divergence outcome', () => {
    set(state.status, 'no_divergence');
    set(state.summary, 'No persistent divergence found');
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="divergence-outcome-summary"]').text()).toBe('No persistent divergence found');
  });

  it('should show no status for a diverged result, whose comparison is the outcome', () => {
    set(state.status, 'diverged');
    set(state.summary, 'balance_divergence.checked');
    set(state.summaryInFooter, true);
    set(state.boundaries, [boundary]);
    const wrapper = mountDiagnostic();
    expect(wrapper.find('[data-testid="divergence-outcome"]').exists()).toBe(false);
  });

  it('should explain a no-checkpoints outcome without an error, boundary or mismatch advice', () => {
    set(state.status, 'no_checkpoints');
    set(state.summary, 'balance_divergence.no_checkpoints');
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="divergence-outcome-summary"]').text()).toBe('balance_divergence.no_checkpoints');
    expect(wrapper.find('[data-testid="test-divergence-boundary"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="data-issue-divergence-error"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="divergence-outcome-next-step"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="data-issue-find-divergence"]').attributes('disabled')).toBeUndefined();
  });

  it('should leave the next step of a diverged result to its search window', () => {
    set(state.status, 'diverged');
    set(state.boundaries, [boundary]);
    const wrapper = mountDiagnostic();
    expect(wrapper.find('[data-testid="divergence-outcome-next-step"]').exists()).toBe(false);
  });

  it('should move the summary into the comparison footer once there are boundary events', () => {
    set(state.status, 'diverged');
    set(state.summary, 'balance_divergence.checked');
    set(state.summaryInFooter, true);
    set(state.boundaries, [boundary]);
    const wrapper = mountDiagnostic();
    expect(wrapper.find('[data-testid="divergence-outcome-summary"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="test-divergence-footer"]').text()).toBe('balance_divergence.checked');
  });

  it('should keep a no-divergence summary as the result even though it returns a last matching event', () => {
    set(state.status, 'no_divergence');
    set(state.summary, 'balance_divergence.no_divergence');
    set(state.boundaries, [boundary]);
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="divergence-outcome-summary"]').text()).toBe('balance_divergence.no_divergence');
    expect(wrapper.get('[data-testid="test-divergence-footer"]').text()).toBe('');
  });

  it('should offer to search again once a search has run', () => {
    const before = mountDiagnostic();
    expect(before.get('[data-testid="data-issue-find-divergence"]').text()).toBe('balance_divergence.action');
    set(state.status, 'no_divergence');
    const after = mountDiagnostic();
    expect(after.get('[data-testid="data-issue-find-divergence"]').text()).toBe('balance_divergence.search_again');
  });

  it.each([
    ['diverged_from_start', 'data_issues.detail.divergence_from_start'],
    ['no_divergence', 'data_issues.detail.divergence_no_mismatch'],
  ] as const)('should suggest the next step for a %s result', (status, message) => {
    set(state.status, status);
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="divergence-outcome-next-step"]').text()).toBe(message);
  });

  it('should suggest no next step before a search has run', () => {
    const wrapper = mountDiagnostic();
    expect(wrapper.find('[data-testid="divergence-outcome-next-step"]').exists()).toBe(false);
  });

  it('should refer a failed search to the dock without repeating its error or hiding the result and retry action', () => {
    set(diagnostic.error, 'Archive request failed');
    set(state.boundaries, [boundary]);
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="data-issue-divergence-error"]').text()).toBe('balance_divergence.search_failed');
    expect(wrapper.text()).not.toContain('Archive request failed');
    expect(wrapper.get('[data-testid="test-divergence-boundary"]').text()).toBe('123');
    expect(wrapper.get('[data-testid="data-issue-find-divergence"]').attributes('disabled')).toBeUndefined();
  });

  it('should omit the section for an unsupported issue', () => {
    set(state.available, false);
    const wrapper = mountDiagnostic();
    expect(wrapper.find('[data-testid="data-issue-balance-divergence"]').exists()).toBe(false);
  });
});
