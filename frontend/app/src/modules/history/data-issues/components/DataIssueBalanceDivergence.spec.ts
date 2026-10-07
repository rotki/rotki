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
    }),
    key: 'first_diverged',
  };
  const state = {
    available: ref<boolean>(true),
    boundaries: ref<DivergenceBoundaryEvent[]>([]),
    canSearch: ref<boolean>(true),
    missingArchive: ref<boolean>(false),
    summary: ref<string>(),
  };
  return {
    boundary,
    diagnostic: {
      available: computed<boolean>(() => get(state.available)),
      boundaries: computed<DivergenceBoundaryEvent[]>(() => get(state.boundaries)),
      canSearch: computed<boolean>(() => get(state.canSearch)),
      chain: computed<string | undefined>(() => 'eth'),
      error: ref<string>(),
      loading: ref<boolean>(false),
      missingArchive: computed<boolean>(() => get(state.missingArchive)),
      search: vi.fn<() => Promise<void>>(),
      summary: computed<string | undefined>(() => get(state.summary)),
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
        DivergenceBoundaryCard: {
          emits: ['view'],
          props: ['boundary', 'asset', 'location'],
          template: '<button data-testid="test-divergence-boundary" @click="$emit(\'view\')">{{ boundary.event.eventIdentifier }}</button>',
        },
        HistoryEventNote: { props: ['notes'], template: '<span>{{ notes }}</span>' },
        I18nT: { template: '<span><slot name="chain" /><slot name="link" /></span>' },
        InternalLink: { template: '<a><slot /></a>' },
        RuiAlert: { template: '<div><slot /></div>' },
        RuiButton: { props: ['disabled', 'loading'], template: '<button :disabled="disabled"><slot /></button>' },
        RuiIcon: true,
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
    set(state.missingArchive, false);
    set(state.boundaries, []);
    set(state.summary, undefined);
    set(diagnostic.error, undefined);
  });

  it('should display the issue time and start diagnosis from the detail-panel action', async () => {
    const wrapper = mountDiagnostic();
    expect(wrapper.text()).toContain('1710000000123');
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

  it('should show a settings link and disable search when an archive node is missing', () => {
    set(state.missingArchive, true);
    set(state.canSearch, false);
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="data-issue-divergence-missing-archive"]').text()).toContain('balance_divergence.settings_link');
    expect(wrapper.get('[data-testid="data-issue-find-divergence"]').attributes('disabled')).toBeDefined();
  });

  it('should disable search while an issue action is busy', () => {
    const wrapper = mountDiagnostic(true);
    expect(wrapper.get('[data-testid="data-issue-find-divergence"]').attributes('disabled')).toBeDefined();
  });

  it('should render the diagnosis summary including a no-divergence outcome', () => {
    set(state.summary, 'No persistent divergence found');
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="data-issue-divergence-summary"]').text()).toBe('No persistent divergence found');
  });

  it('should show a failed search without hiding the retry action', () => {
    set(diagnostic.error, 'Archive request failed');
    const wrapper = mountDiagnostic();
    expect(wrapper.get('[data-testid="data-issue-divergence-error"]').text()).toBe('Archive request failed');
    expect(wrapper.get('[data-testid="data-issue-find-divergence"]').attributes('disabled')).toBeUndefined();
  });

  it('should omit the section for an unsupported issue', () => {
    set(state.available, false);
    const wrapper = mountDiagnostic();
    expect(wrapper.find('[data-testid="data-issue-balance-divergence"]').exists()).toBe(false);
  });
});
