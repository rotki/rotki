import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { HistoryEventsTableSource } from '@/modules/history/events/types';
import type { UseHistoryEventsTableReturn } from '@/modules/history/events/use-history-events-table';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type Component, defineComponent, h } from 'vue';
import { RequestFailed, type RequestFailure } from '@/modules/core/api/request-result';
import { provideTableFetchError } from '@/modules/core/table/use-table-empty-state';
import HistoryEventsVirtualTable from '@/modules/history/events/components/HistoryEventsVirtualTable.vue';
import { createRuiPlugin } from '@/plugins/rui';
import '@test/i18n';

vi.mock('@/modules/history/events/components/RedecodeConfirmationDialog.vue', () => ({
  __esModule: true,
  default: defineComponent({ name: 'RedecodeConfirmationDialog', render: () => null }),
}));

/** What the mocked table shell reports at the next mount. */
const shellState: { eventsError?: RequestFailure; groups: HistoryEventEntry[] } = { groups: [] };
const retryEvents = vi.fn<() => Promise<void>>();

/**
 * An empty virtual list, typed directly: passed through `createMock`'s deep-partial overrides, its
 * element ref makes the type instantiation too deep for the compiler.
 */
function emptyVirtualList(): UseHistoryEventsTableReturn['virtual'] {
  return {
    containerProps: { onScroll: vi.fn(), ref: ref<HTMLElement | null>(null), style: {} },
    list: ref([]),
    wrapperProps: computed(() => ({ style: { height: '0px', marginTop: '0px', width: '100%' } })),
  };
}

vi.mock('@/modules/history/events/use-history-events-table', () => ({
  useHistoryEventsTable: (): UseHistoryEventsTableReturn => Object.assign(createMock<UseHistoryEventsTableReturn>({
    redecode: {
      hasCustomEvents: ref<boolean>(false),
      modelShow: ref<boolean>(false),
      payload: ref(),
      showIndexerOptions: ref<boolean>(false),
    },
    shell: {
      entriesFoundTotal: computed<number | undefined>(() => undefined),
      eventsError: shallowRef<RequestFailure | undefined>(shellState.eventsError),
      found: computed<number>(() => 0),
      groups: computed<HistoryEventEntry[]>(() => shellState.groups),
      loading: ref<boolean>(false),
      retryEvents,
      showUpgradeRow: computed<boolean>(() => false),
      total: computed<number>(() => 0),
    },
  }), { virtual: emptyVirtualList() }),
}));

const source: HistoryEventsTableSource = {
  excludeIgnored: true,
  groupLoading: false,
  groups: { data: [], found: 0, limit: -1, total: 0 },
  requestPayload: undefined,
};

/** Mounts the table under a view that provides `error`, the way `useServerTable` does. */
function mountUnder(error: Ref<unknown>, props: { hasActiveFilters?: boolean } = {}): VueWrapper {
  const host: Component = defineComponent({
    setup() {
      provideTableFetchError(error);
      return (): ReturnType<typeof h> => h(HistoryEventsVirtualTable, {
        pagination: { limit: 10, page: 1, total: 0 },
        sort: [],
        source,
        ...props,
      });
    },
  });

  return mount(host, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: { HistoryEventsVirtualHeader: true },
    },
  });
}

describe('historyEventsVirtualTable', () => {
  describe('when the groups could not be fetched', () => {
    it('should name the failure where the events would have been', () => {
      const wrapper = mountUnder(ref(RequestFailed({ cause: undefined, message: 'backend is down' })));

      expect(wrapper.find('[data-testid=history-events-fetch-error]').text()).toBe('backend is down');
      expect(wrapper.text()).not.toContain('transactions.empty_state.no_events');
    });

    it('should prefer the failure over the clear-filters prompt', () => {
      const wrapper = mountUnder(ref(RequestFailed({ cause: undefined, message: 'backend is down' })), { hasActiveFilters: true });

      expect(wrapper.find('[data-testid=history-events-fetch-error]').exists()).toBe(true);
      expect(wrapper.text()).not.toContain('transactions.empty_state.no_data_with_filters');
    });

    it('should ask its owner to fetch again from the retry', async () => {
      const wrapper = mountUnder(ref(RequestFailed({ cause: undefined, message: 'backend is down' })));

      await wrapper.find('button').trigger('click');

      expect(wrapper.findComponent(HistoryEventsVirtualTable).emitted('refetch')).toHaveLength(1);
    });
  });

  describe('when the groups loaded but their events could not be fetched', () => {
    beforeEach(() => {
      shellState.eventsError = RequestFailed({ cause: undefined, message: 'events request failed' });
      shellState.groups = [createMock<HistoryEventEntry>()];
      retryEvents.mockClear();
    });

    afterEach(() => {
      shellState.eventsError = undefined;
      shellState.groups = [];
    });

    it('should show the reason above the rows', () => {
      const wrapper = mountUnder(ref<unknown>());

      expect(wrapper.find('[data-testid=history-events-events-error]').text()).toContain('events request failed');
    });

    it('should load the events again from the retry', async () => {
      const wrapper = mountUnder(ref<unknown>());

      await wrapper.find('[data-testid=history-events-events-retry]').trigger('click');

      expect(retryEvents).toHaveBeenCalledOnce();
    });
  });

  it('should say there are no events when the fetch succeeded empty', () => {
    const wrapper = mountUnder(ref<unknown>());

    expect(wrapper.find('[data-testid=history-events-fetch-error]').exists()).toBe(false);
    expect(wrapper.text()).toContain('transactions.empty_state.no_events');
  });
});
