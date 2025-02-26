import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { isOfEventType } from '@/utils/history/events';
import { useHistoryTransactions } from '@/composables/history/events/tx';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useHistoryEvents } from '@/composables/history/events';
import type {
  EditEvmHistoryEventPayload,
  EvmHistoryEvent,
  HistoryEventEntry,
} from '@/types/history/events';
import type { EvmChainInfo } from '@/types/api/chains';
import type { Blockchain } from '@rotki/common';

vi.mock('@/store/tasks', async () => {
  const { ref } = await import('vue');
  return {
    useTaskStore: vi.fn().mockReturnValue({
      isTaskRunning: vi.fn().mockImplementation(() => ref(false)),
      awaitTask: vi.fn().mockResolvedValue({}),
    }),
  };
});

vi.mock('@/composables/api/history/events', async () => {
  const { camelCaseTransformer } = await import('@/services/axios-transformers.ts');
  const historyEvents = await import('../../../fixtures/history-events.json');
  return {
    useHistoryEventsApi: vi.fn().mockReturnValue({
      addTransactionHash: vi.fn(),
      fetchTransactionsTask: vi.fn().mockResolvedValue({}),
      deleteHistoryEvent: vi.fn(),
      decodeTransactions: vi.fn().mockResolvedValue({}),
      redecodeMissingEvents: vi.fn(),
      addHistoryEvent: vi.fn(),
      editHistoryEvent: vi.fn(),
      queryOnlineHistoryEvents: vi.fn().mockResolvedValue({}),
      fetchHistoryEvents: vi.fn().mockResolvedValue(camelCaseTransformer(historyEvents.result)),
    }),
  };
});

vi.mock('@/composables/info/chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      txChains: computed(() => [
        {
          evmChainName: 'ethereum',
          id: Blockchain.ETH,
          type: 'evm',
          name: 'Ethereum',
          image: '',
          nativeToken: 'ETH',
        } satisfies EvmChainInfo,
      ]),
      getChain: () => Blockchain.ETH,
      getChainName: () => 'Ethereum',
      getEvmChainName: (_chain: string) => 'ethereum',
      getNativeAsset: (chain: Blockchain) => chain,
      getChainImageUrl: (chain: Blockchain) => `${chain}.png`,
      isEvmLikeChains: (_chain: string) => false,
    }),
  };
});

describe('composables::history/events/tx', () => {
  let events: HistoryEventEntry[];

  beforeAll(async () => {
    setActivePinia(createPinia());

    const eventsCollection = await useHistoryEvents().fetchHistoryEvents({
      limit: -1,
      offset: 0,
      eventIdentifiers: [],
      groupByEventIds: false,
    });

    events = eventsCollection.data;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('initialize composable correctly', async () => {
    const eventsApi = useHistoryEventsApi();
    const addHistorySpy = vi.spyOn(eventsApi, 'addTransactionHash');
    const addHistoryEventSpy = vi.spyOn(eventsApi, 'addHistoryEvent');
    const editHistoryEventSpy = vi.spyOn(eventsApi, 'editHistoryEvent');
    const decodeTxSpy = vi.spyOn(eventsApi, 'decodeTransactions');
    const deleteHistoryEventSpy = vi.spyOn(eventsApi, 'deleteHistoryEvent');
    const queryEvSpy = vi.spyOn(eventsApi, 'queryOnlineHistoryEvents');

    const event = events[0];
    assert(isOfEventType<EvmHistoryEvent>(event, 'evm event'));

    const editEvent: EditEvmHistoryEventPayload = { ...event, identifier: 1 };

    const { addTransactionHash, refreshTransactions } = useHistoryTransactions();
    const { redecodeTransactions } = useHistoryTransactionDecoding();
    const { addHistoryEvent, editHistoryEvent, deleteHistoryEvent } = useHistoryEvents();

    // add a hash and check the spy function is called
    await addTransactionHash({
      txHash: '0x9',
      associatedAddress: '0x0...',
      evmChain: '',
    });

    expect(addHistorySpy).toHaveBeenCalledOnce();

    // add a transaction event and check the spy function is called
    await addHistoryEvent(event);
    expect(addHistoryEventSpy).toHaveBeenCalledOnce();
    expect(addHistoryEventSpy).toHaveBeenCalledWith(event);

    // edit a transaction and check the spy function is called
    await editHistoryEvent(editEvent);

    expect(editHistoryEventSpy).toHaveBeenCalledOnce();
    expect(editHistoryEventSpy).toHaveBeenCalledWith(editEvent);

    // fetch transactions and check the spy function is called
    await redecodeTransactions();

    expect(decodeTxSpy).toHaveBeenCalledOnce();
    expect(decodeTxSpy).toHaveBeenCalledWith(expect.anything(), expect.anything(), true);

    // delete transaction with empty array and check the spy function is not called
    await deleteHistoryEvent([], true);

    expect(deleteHistoryEventSpy).toHaveBeenCalledOnce();
    expect(deleteHistoryEventSpy).toHaveBeenCalledWith([], true);

    // add a transaction and check the spy function is called
    await refreshTransactions();
    expect(queryEvSpy).toHaveBeenCalledTimes(0);

    // fetch all transaction and check the spy function is called
    await redecodeTransactions();

    expect(decodeTxSpy).toHaveBeenCalledTimes(2);
  });
});
