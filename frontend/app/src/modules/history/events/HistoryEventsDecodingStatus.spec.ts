import type { EvmUnDecodedTransactionsData, ProtocolCacheUpdatesData } from '@/modules/core/messaging/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HistoryEventsDecodingStatus from '@/modules/history/events/HistoryEventsDecodingStatus.vue';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';

const { checkMissingEventsAndRedecode, isActive } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    checkMissingEventsAndRedecode: vi.fn(),
    isActive: ref<boolean>(false),
  };
});

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({
    useIsActive: (): typeof isActive => isActive,
  }),
}));

vi.mock('@/modules/history/events/tx/use-history-transaction-decoding', () => ({
  useHistoryTransactionDecoding: (): Record<string, unknown> => ({ checkMissingEventsAndRedecode }),
}));

const wrappers: VueWrapper[] = [];

function undecoded(evmChain: string, processed: number, total: number): EvmUnDecodedTransactionsData {
  return { chain: evmChain, processed, total };
}

function cacheUpdate(): ProtocolCacheUpdatesData {
  return { chain: 'ethereum', processed: 3, protocol: 'curve', total: 9 };
}

async function mountStatus(decodingStatus: EvmUnDecodedTransactionsData[] = []): Promise<VueWrapper> {
  const wrapper = mount(HistoryEventsDecodingStatus, {
    global: { provide: libraryDefaults },
    props: { decodingStatus, refreshing: false },
  });
  wrappers.push(wrapper);
  await flushPromises();
  return wrapper;
}

function rowsOf(wrapper: VueWrapper): Array<Record<string, unknown>> {
  return wrapper.findComponent({ name: 'RuiDataTable' }).props('rows');
}

describe('modules/history/events/HistoryEventsDecodingStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createCustomPinia());
    set(isActive, false);
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  describe('what it asks its parent to do', () => {
    it('should ask for a reset on mount when there is nothing left undecoded', async () => {
      const wrapper = await mountStatus([]);

      expect(wrapper.emitted('reset-undecoded-transactions')).toHaveLength(1);
    });

    it('should not ask for a reset while transactions are still undecoded', async () => {
      const wrapper = await mountStatus([undecoded('ethereum', 1, 4)]);

      expect(wrapper.emitted('reset-undecoded-transactions')).toBeUndefined();
    });

    it('should ask for a redecode rather than decoding anything itself', async () => {
      const wrapper = await mountStatus([undecoded('ethereum', 1, 4)]);

      await wrapper.find('[data-testid="redecode-all"]').trigger('click');

      expect(wrapper.emitted('redecode-all-events')).toHaveLength(1);
      expect(checkMissingEventsAndRedecode).not.toHaveBeenCalled();
    });
  });

  describe('when decoding finishes', () => {
    it('should ask for a reset, so the parent stops showing stale progress', async () => {
      set(isActive, true);
      const wrapper = await mountStatus([undecoded('ethereum', 1, 4)]);

      set(isActive, false);
      await flushPromises();

      expect(wrapper.emitted('reset-undecoded-transactions')).toHaveLength(1);
    });

    it('should ask twice when the list is already empty, refresh having asked once too', async () => {
      set(isActive, true);
      const wrapper = await mountStatus([]);
      const onMount = wrapper.emitted('reset-undecoded-transactions')?.length ?? 0;

      set(isActive, false);
      await flushPromises();

      expect((wrapper.emitted('reset-undecoded-transactions')?.length ?? 0) - onMount).toBe(2);
    });

    it('should ask for nothing while decoding is still running', async () => {
      const wrapper = await mountStatus([undecoded('ethereum', 1, 4)]);

      set(isActive, true);
      await flushPromises();

      expect(wrapper.emitted('reset-undecoded-transactions')).toBeUndefined();
    });
  });

  describe('the rows it renders', () => {
    it('should show the most recent chain first', async () => {
      const wrapper = await mountStatus([
        undecoded('ethereum', 1, 4),
        undecoded('optimism', 2, 5),
      ]);

      expect(rowsOf(wrapper).map(row => row.chain)).toEqual(['optimism', 'ethereum']);
    });

    it('should render no table at all when nothing is undecoded', async () => {
      const wrapper = await mountStatus([]);

      expect(wrapper.findComponent({ name: 'RuiDataTable' }).exists()).toBe(false);
    });

    it('should put a protocol cache refresh above the chains while one is running', async () => {
      useProtocolCacheStatusStore().setProtocolCacheStatus(cacheUpdate());

      const wrapper = await mountStatus([undecoded('optimism', 2, 5)]);

      expect(rowsOf(wrapper)[0]).toMatchObject({ chain: 'ethereum', processed: 0, total: 0 });
      expect(rowsOf(wrapper)).toHaveLength(2);
    });

    it('should leave the chains alone when no cache refresh is running', async () => {
      const wrapper = await mountStatus([undecoded('optimism', 2, 5)]);

      expect(rowsOf(wrapper)).toHaveLength(1);
    });
  });
});
