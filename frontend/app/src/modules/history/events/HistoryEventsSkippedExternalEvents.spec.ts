import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HistoryEventsSkippedExternalEvents from '@/modules/history/events/HistoryEventsSkippedExternalEvents.vue';

const state = await vi.hoisted(async () => {
  const { ref, shallowRef } = await import('vue');
  return {
    reProcessSkippedEvents: vi.fn<() => Promise<void>>(),
    reprocessFailure: shallowRef<unknown>(),
    reprocessNote: ref<string>(),
  };
});

vi.mock('@/modules/history/events/use-skipped-events-actions', async () => {
  const { computed, ref } = await import('vue');
  return {
    useSkippedEventsActions: (): Record<string, unknown> => ({
      exportCSV: vi.fn(),
      loading: ref<boolean>(false),
      locationsData: computed(() => []),
      reProcessSkippedEvents: state.reProcessSkippedEvents,
      reprocessFailure: state.reprocessFailure,
      reprocessNote: state.reprocessNote,
      skippedEvents: ref({ locations: { kraken: 2 }, total: 2 }),
    }),
  };
});

function mountRow(): VueWrapper {
  return mount(HistoryEventsSkippedExternalEvents, {
    global: { stubs: { LocationDisplay: true, RuiDataTable: true, SettingsItem: { template: '<div><slot /></div>' } } },
  });
}

describe('historyEventsSkippedExternalEvents', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(state.reprocessFailure, undefined);
    set(state.reprocessNote, undefined);
  });

  it('should name a failed reprocess on the row, with a retry that reprocesses again', async () => {
    set(state.reprocessFailure, new Error('decoder crashed'));
    const wrapper = mountRow();

    const strip = wrapper.find('[data-testid=skipped-events-reprocess-failure]');
    expect(strip.text()).toContain('transactions.events.skipped.reprocess.failed.title');
    expect(strip.text()).toContain('decoder crashed');

    await strip.find('[data-testid=failure-strip-retry]').trigger('click');
    expect(state.reProcessSkippedEvents).toHaveBeenCalledOnce();
  });

  it('should note a partial run on the row', () => {
    set(state.reprocessNote, 'transactions.events.skipped.reprocess.success.some');
    const wrapper = mountRow();

    expect(wrapper.find('[data-testid=skipped-events-reprocess-note]').text()).toBe('transactions.events.skipped.reprocess.success.some');
    expect(wrapper.find('[data-testid=skipped-events-reprocess-failure]').exists()).toBe(false);
  });

  it('should show neither while the last run went through whole', () => {
    const wrapper = mountRow();

    expect(wrapper.find('[data-testid=skipped-events-reprocess-failure]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=skipped-events-reprocess-note]').exists()).toBe(false);
  });
});
