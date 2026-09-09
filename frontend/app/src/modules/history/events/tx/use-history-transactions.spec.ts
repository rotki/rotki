import type { SubmittedSpec } from '@test/utils/mocks/native-task';
import type { EvmChainInfo } from '@/modules/core/api/types/chains';
import type {
  EditEvmHistoryEventPayload,
  EvmHistoryEvent,
  HistoryEventRow,
} from '@/modules/history/events/schemas';
import type { RunBackendTask } from '@/modules/task-center/use-native-task';
import { assert, type Blockchain } from '@rotki/common';
import { err, ok, type Result } from 'plainfp/result';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { isOfEventType } from '@/modules/history/event-utils';
import { useHistoryTransactionDecoding } from '@/modules/history/events/tx/use-history-transaction-decoding';
import { useHistoryTransactions } from '@/modules/history/events/tx/use-history-transactions';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: vi.fn().mockImplementation(async (taskFn: () => Promise<unknown>): Promise<unknown> => {
      await taskFn();
      return { success: true, result: {} };
    }),
  }),
}));

/**
 * The submitted specs, so a test can assert what a re-pull was scheduled as, and the outcome the
 * task runner hands back, so a test can drive the failure branches.
 */
const {
  addTransactionHash,
  notifyError,
  notifyInfo,
  repullingEthStakingEvents,
  repullingExchangeEvents,
  repullingTransactions,
} = vi.hoisted(() => ({
  addTransactionHash: vi.fn(),
  notifyError: vi.fn(),
  notifyInfo: vi.fn(),
  repullingEthStakingEvents: vi.fn(),
  repullingExchangeEvents: vi.fn(),
  repullingTransactions: vi.fn(),
}));

/**
 * The submitted specs, so a test can assert what a re-pull was scheduled as, and the outcome the
 * task runner hands back, so a test can drive the failure branches.
 */
const { outcome, submitted } = vi.hoisted((): {
  outcome: { value: Result<unknown, TaskError> | undefined };
  submitted: SubmittedSpec[];
} => ({ outcome: { value: undefined }, submitted: [] }));

vi.mock(import('@/modules/task-center/use-native-task'), async (importOriginal) => {
  const actual = await importOriginal();
  const { ok } = await import('plainfp/result');
  const { runSpecWith } = await import('@test/utils/mocks/native-task');
  return {
    ...actual,
    useNativeTask: vi.fn().mockReturnValue({
      cancelByType: vi.fn(() => vi.fn()),
      reportProgress: vi.fn(),
      statusOf: vi.fn(() => ({ active: false, everCompleted: false, pending: false, running: false })),
      submitTask: vi.fn(async (spec: SubmittedSpec) => {
        submitted.push(spec);
        const runTask: RunBackendTask = async <R>(taskFn: () => Promise<{ taskId: number }>): Promise<Result<R, TaskError>> => {
          const result = await taskFn();
          // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the stub stands in for a runner whose result type only its caller knows
          return (outcome.value ?? ok(result)) as Result<R, TaskError>;
        };
        return runSpecWith(runTask)(spec);
      }),
    }),
  };
});

vi.mock('@/modules/core/tasks/use-task-store', async () => {
  const { ref } = await import('vue');
  return {
    useTaskStore: vi.fn().mockReturnValue({
      useIsTaskRunning: vi.fn().mockImplementation(() => ref(false)),
      isTaskRunning: vi.fn().mockImplementation(() => false),
    }),
  };
});

vi.mock('@/modules/core/notifications/use-notifications', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useNotifications: vi.fn().mockReturnValue({
      notifyError,
      notifyInfo,
      removeMatching: vi.fn(),
      showErrorMessage: vi.fn(),
      showSuccessMessage: vi.fn(),
    }),
  };
});

vi.mock('@/modules/history/api/events/use-history-events-api', async () => {
  const { camelCaseTransformer } = await import('@/modules/core/api/transformers');
  const historyEvents = await import('@test/fixtures/history-events.json');
  return {
    useHistoryEventsApi: vi.fn().mockReturnValue({
      addTransactionHash,
      repullingEthStakingEvents,
      repullingExchangeEvents,
      repullingTransactions,
      fetchTransactionsTask: vi.fn().mockResolvedValue({}),
      deleteHistoryEvent: vi.fn(),
      decodeTransactions: vi.fn().mockResolvedValue({}),
      getUndecodedTransactionsBreakdown: vi.fn().mockResolvedValue({}),
      redecodeMissingEvents: vi.fn(),
      addHistoryEvent: vi.fn(),
      editHistoryEvent: vi.fn(),
      queryOnlineHistoryEvents: vi.fn().mockResolvedValue({}),
      fetchHistoryEvents: vi.fn().mockResolvedValue(camelCaseTransformer(historyEvents.result)),
    }),
  };
});

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      decodableTxChainsInfo: computed(() => [
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

/** Clears what the last re-pull left behind, so an id or a notification is this test's alone. */
function reset(): void {
  vi.clearAllMocks();
  submitted.length = 0;
  outcome.value = undefined;
}

describe('useHistoryTransactions', () => {
  let events: HistoryEventRow[];

  beforeAll(async () => {
    setActivePinia(createPinia());

    const eventsCollection = await useHistoryEvents().fetchHistoryEvents({
      limit: -1,
      offset: 0,
      groupIdentifiers: [],
      aggregateByGroupIds: false,
    });

    events = eventsCollection.data;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize composable correctly', async () => {
    const eventsApi = useHistoryEventsApi();
    const addHistorySpy = vi.spyOn(eventsApi, 'addTransactionHash');
    const addHistoryEventSpy = vi.spyOn(eventsApi, 'addHistoryEvent');
    const editHistoryEventSpy = vi.spyOn(eventsApi, 'editHistoryEvent');
    const decodeTxSpy = vi.spyOn(eventsApi, 'decodeTransactions');
    const deleteHistoryEventSpy = vi.spyOn(eventsApi, 'deleteHistoryEvent');
    const queryEvSpy = vi.spyOn(eventsApi, 'queryOnlineHistoryEvents');

    const event = events[0];
    assert(!Array.isArray(event));
    assert(isOfEventType<EvmHistoryEvent>(event, 'evm event'));

    const editEvent: EditEvmHistoryEventPayload = { ...event, identifier: 1 };

    const { addTransactionHash, refreshTransactions } = useHistoryTransactions();
    const { redecodeTransactions } = useHistoryTransactionDecoding();
    const { addHistoryEvent, editHistoryEvent, deleteHistoryEvent } = useHistoryEvents();

    // add a hash and check the spy function is called
    await addTransactionHash({
      txRef: '0x9',
      associatedAddress: '0x0...',
      blockchain: '',
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
    expect(decodeTxSpy).toHaveBeenCalledWith(expect.anything(), true);

    // delete transaction with empty array and check the spy function is not called
    await deleteHistoryEvent([], true);

    expect(deleteHistoryEventSpy).toHaveBeenCalledOnce();
    expect(deleteHistoryEventSpy).toHaveBeenCalledWith({ identifiers: [] }, true);

    // add a transaction and check the spy function is called
    await refreshTransactions();
    expect(queryEvSpy).toHaveBeenCalledTimes(0);

    // fetch all transaction and check the spy function is called
    await redecodeTransactions();

    expect(decodeTxSpy).toHaveBeenCalledTimes(2);
  });

  describe('addTransactionHash', () => {
    beforeEach(() => {
      addTransactionHash.mockReset();
    });

    it('should report a hash that was accepted', async () => {
      const result = await useHistoryTransactions().addTransactionHash({
        associatedAddress: '0x0',
        blockchain: 'eth',
        txRef: '0x9',
      });

      expect(result).toEqual({ message: '', success: true });
    });

    it('should report the message a rejection carried', async () => {
      addTransactionHash.mockRejectedValue(new Error('already tracked'));

      const result = await useHistoryTransactions().addTransactionHash({
        associatedAddress: '0x0',
        blockchain: 'eth',
        txRef: '0x9',
      });

      expect(result).toEqual({ message: 'already tracked', success: false });
    });

    /** A form needs the failure per field, not one message covering the whole submission. */
    it('should report a validation failure against the fields it names', async () => {
      addTransactionHash.mockRejectedValue(new ApiValidationError('{"txRef":["not a transaction hash"]}'));

      const result = await useHistoryTransactions().addTransactionHash({
        associatedAddress: '0x0',
        blockchain: 'eth',
        txRef: 'nonsense',
      });

      assert(!result.success);
      expect(result.message).toEqual({ txRef: ['not a transaction hash'] });
    });
  });

  /**
   * A re-pull is scheduled as one activity, and its identity is what stops two different requests
   * being taken for the same one. An absent bound is part of that identity: "everything before X"
   * is a different request from "X to Y".
   */
  describe('repullingTransactions', () => {
    beforeEach(() => {
      reset();
      repullingTransactions.mockResolvedValue({});
    });

    it('should hand back what the re-pull found', async () => {
      const found = { newTransactions: { eth: ['0x1'] }, newTransactionsCount: 1 };
      outcome.value = ok(found);

      expect(await useHistoryTransactions().repullingTransactions({})).toEqual(found);
    });

    it('should tell two bounded ranges apart', async () => {
      const { repullingTransactions: repull } = useHistoryTransactions();

      await repull({ fromTimestamp: 1, toTimestamp: 2 });
      await repull({ fromTimestamp: 3, toTimestamp: 4 });

      expect(submitted[0].id).not.toBe(submitted[1].id);
    });

    it('should tell an open-ended range from a bounded one', async () => {
      const { repullingTransactions: repull } = useHistoryTransactions();

      await repull({ toTimestamp: 2 });
      await repull({ fromTimestamp: 1, toTimestamp: 2 });

      expect(submitted[0].id).not.toBe(submitted[1].id);
    });

    it('should treat the same request as the same activity', async () => {
      const { repullingTransactions: repull } = useHistoryTransactions();

      await repull({ address: '0x0', chain: 'eth' });
      await repull({ address: '0x0', chain: 'eth' });

      expect(submitted[0].id).toBe(submitted[1].id);
    });

    /** Without an address and chain there is no account to name, so the wording differs. */
    it('should name the account it is re-pulling for', async () => {
      await useHistoryTransactions().repullingTransactions({ address: '0x0', chain: 'eth' });

      expect(submitted[0].subtitle).toContain('actions.repulling_transaction.task.description');
    });

    it('should say when there is no account to name', async () => {
      await useHistoryTransactions().repullingTransactions({});

      expect(submitted[0].subtitle)
        .toContain('actions.repulling_transaction.task.no_address_or_chain_transaction');
    });

    it('should report a failure and hand back nothing', async () => {
      outcome.value = err(TaskFailed({ message: 'the backend gave up' }));

      expect(await useHistoryTransactions().repullingTransactions({})).toBeUndefined();
      expect(notifyError).toHaveBeenCalledWith(
        'actions.repulling_transaction.task.title',
        expect.stringContaining('actions.repulling_transaction.error.no_address_or_chain_transaction'),
      );
    });

    /** The user asked for the cancellation, so there is nothing to report back to them. */
    it('should stay quiet about a cancellation', async () => {
      outcome.value = err(Cancelled({ message: 'cancelled' }));

      expect(await useHistoryTransactions().repullingTransactions({})).toBeUndefined();
      expect(notifyError).not.toHaveBeenCalled();
    });
  });

  describe('repullingExchangeEvents', () => {
    const payload = { location: 'kraken', name: 'my kraken' };

    beforeEach(() => {
      reset();
      repullingExchangeEvents.mockResolvedValue({});
    });

    it('should report events were stored', async () => {
      outcome.value = ok({ storedEvents: 4 });

      expect(await useHistoryTransactions().repullingExchangeEvents(payload)).toBe(true);
      expect(notifyInfo).toHaveBeenCalledWith(
        'actions.repulling_exchange_events.task.title',
        expect.stringContaining('actions.repulling_exchange_events.success.description'),
      );
    });

    /** A re-pull that found nothing still succeeded, so it is reported rather than left silent. */
    it('should say so when it found nothing', async () => {
      outcome.value = ok({ storedEvents: 0 });

      expect(await useHistoryTransactions().repullingExchangeEvents(payload)).toBe(false);
      expect(notifyInfo).toHaveBeenCalledWith(
        'actions.repulling_exchange_events.task.title',
        'actions.repulling_exchange_events.success.no_events_description',
      );
    });

    it('should report a failure', async () => {
      outcome.value = err(TaskFailed({ message: 'the backend gave up' }));

      expect(await useHistoryTransactions().repullingExchangeEvents(payload)).toBe(false);
      expect(notifyError).toHaveBeenCalled();
      expect(notifyInfo).not.toHaveBeenCalled();
    });

    it('should stay quiet about a cancellation', async () => {
      outcome.value = err(Cancelled({ message: 'cancelled' }));

      expect(await useHistoryTransactions().repullingExchangeEvents(payload)).toBe(false);
      expect(notifyError).not.toHaveBeenCalled();
    });
  });

  describe('repullingEthStakingEvents', () => {
    const payload = { entryType: 'eth withdrawal event' };

    beforeEach(() => {
      reset();
      repullingEthStakingEvents.mockResolvedValue({});
    });

    /** The counts are what the user came for, so they are broken down rather than totalled away. */
    it('should break the total down per validator and per address', async () => {
      outcome.value = ok({ perAddress: { '0xabc': 2 }, perValidator: { 12: 3 }, total: 5 });

      expect(await useHistoryTransactions().repullingEthStakingEvents(payload)).toBe(true);

      const [, message] = notifyInfo.mock.calls[0];
      expect(message).toContain('actions.repulling_eth_staking.success.per_validator');
      expect(message).toContain('actions.repulling_eth_staking.success.validator_entry');
      expect(message).toContain('actions.repulling_eth_staking.success.per_address');
      expect(message).toContain('actions.repulling_eth_staking.success.address_entry');
    });

    /** A breakdown with nothing in it is dropped rather than left as a blank block at the end. */
    it('should leave out a breakdown it has nothing for', async () => {
      outcome.value = ok({ perAddress: {}, perValidator: { 12: 3 }, total: 3 });

      await useHistoryTransactions().repullingEthStakingEvents(payload);

      const [, message] = notifyInfo.mock.calls[0];
      expect(message).toContain('actions.repulling_eth_staking.success.per_validator');
      expect(message).not.toContain('actions.repulling_eth_staking.success.per_address');
      expect(message.endsWith('\n')).toBe(false);
    });

    it('should say so when it found nothing', async () => {
      outcome.value = ok({ perAddress: {}, perValidator: {}, total: 0 });

      expect(await useHistoryTransactions().repullingEthStakingEvents(payload)).toBe(false);
      expect(notifyInfo).toHaveBeenCalledWith(
        'actions.repulling_eth_staking.task.title',
        expect.stringContaining('actions.repulling_eth_staking.success.no_events_description'),
      );
    });

    it('should report a failure', async () => {
      outcome.value = err(TaskFailed({ message: 'the backend gave up' }));

      expect(await useHistoryTransactions().repullingEthStakingEvents(payload)).toBe(false);
      expect(notifyError).toHaveBeenCalled();
    });
  });
});
