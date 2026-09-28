import type { EvmUnDecodedTransactionsData } from '@/modules/core/messaging/types';
import { shallowMount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ActivityKind } from '@/modules/task-center/core/types';
import HistoryEventsDecodingStatus from './HistoryEventsDecodingStatus.vue';

const { isDecoding } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { isDecoding: ref<boolean>(false) };
});

vi.mock('@/modules/task-center/use-task-center', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/task-center/use-task-center')>();
  const { computed } = await import('vue');
  return {
    ...actual,
    useTaskCenter: (): object => ({
      useIsActive: (kind: ActivityKind, ...parts: unknown[]) =>
        computed<boolean>(() => kind === ActivityKind.TX_DECODING && parts.length === 0 && isDecoding.value),
    }),
  };
});

vi.mock('@/modules/history/events/tx/use-history-transaction-decoding', () => ({
  useHistoryTransactionDecoding: (): object => ({ checkMissingEventsAndRedecode: vi.fn() }),
}));

const STILL_UNDECODED: EvmUnDecodedTransactionsData[] = [{ chain: 'ethereum', processed: 10, total: 25 }];

function mountStatus(decodingStatus: EvmUnDecodedTransactionsData[]): VueWrapper {
  return shallowMount(HistoryEventsDecodingStatus, {
    props: { decodingStatus, refreshing: false },
    global: { stubs: { RuiCard: { template: '<div><slot name="custom-header" /><slot /></div>' } } },
  });
}

async function finishDecoding(): Promise<void> {
  set(isDecoding, true);
  await nextTick();
  set(isDecoding, false);
  await nextTick();
}

describe('modules/history/events/HistoryEventsDecodingStatus', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(isDecoding, false);
  });

  it('should keep the undecoded transactions listed when a decode finishes with some still left', async () => {
    const wrapper = mountStatus(STILL_UNDECODED);

    await finishDecoding();

    expect(wrapper.emitted('reset-undecoded-transactions')).toBeUndefined();
  });

  it('should clear the status once a decode finishes with nothing listed', async () => {
    const wrapper = mountStatus([]);
    const onMount = wrapper.emitted('reset-undecoded-transactions')?.length ?? 0;

    await finishDecoding();

    expect(wrapper.emitted('reset-undecoded-transactions')).toHaveLength(onMount + 1);
  });
});
