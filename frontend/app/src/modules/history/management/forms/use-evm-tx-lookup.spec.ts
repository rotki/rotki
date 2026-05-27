import type { Ref } from 'vue';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useEvmTxAutoFill } from '@/modules/history/management/forms/use-evm-tx-lookup';

const runTaskMock = vi.fn();
const cancelTaskByTaskTypeMock = vi.fn();

vi.mock('@/modules/core/tasks/use-task-handler', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useTaskHandler: (): Record<string, unknown> => ({
      cancelTask: vi.fn(),
      cancelTaskByTaskType: cancelTaskByTaskTypeMock,
      runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
        await taskFn();
        return runTaskMock(taskFn, ...rest);
      },
    }),
  };
});

vi.mock('@/modules/history/api/events/use-history-events-api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useHistoryEventsApi: vi.fn().mockReturnValue({
      lookupEvmTransaction: vi.fn().mockResolvedValue({ taskId: 1 }),
    }),
  };
});

const VALID_HASH = '0x65d53653c584cde22e559cec4667a7278f75966360590b725d87055fb17552ba';
const VALID_HASH_2 = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
const VALID_ADDRESS = '0xb8553D9ee35dd23BB96fbd679E651B929821969B';

function createPayload(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    blockNumber: 19680000,
    evmChain: 'ethereum',
    fromAddress: VALID_ADDRESS,
    gas: '21000',
    gasPrice: '1000000000',
    gasUsed: '21000',
    nonce: 7,
    timestamp: 1713350400,
    toAddress: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    txHash: VALID_HASH,
    value: '0',
    wasFetched: true,
    ...overrides,
  };
}

interface Setup {
  txHash: Ref<string>;
  evmChain: Ref<string>;
  relatedAddress: Ref<string>;
  enabled: Ref<boolean>;
  errorMessages: Ref<Record<string, string[]>>;
  onResolved: ReturnType<typeof vi.fn>;
  composable: ReturnType<typeof useEvmTxAutoFill>;
}

function mount(initial: Partial<Setup> = {}): Setup {
  const txHash = ref<string>('');
  const evmChain = ref<string>('ethereum');
  const relatedAddress = ref<string>('');
  const enabled = ref<boolean>(true);
  const errorMessages = ref<Record<string, string[]>>({});
  const onResolved = vi.fn();
  const composable = useEvmTxAutoFill({
    debounce: 0,
    enabled,
    errorFields: { relatedAddress: 'locationLabel', txHash: 'txRef' },
    errorMessages,
    evmChain,
    onResolved,
    relatedAddress,
    txHash,
  });
  return { composable, enabled, errorMessages, evmChain, onResolved, relatedAddress, txHash, ...initial };
}

describe('useEvmTxAutoFill', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
    runTaskMock.mockReset();
    cancelTaskByTaskTypeMock.mockReset();
    cancelTaskByTaskTypeMock.mockResolvedValue(undefined);
    const lookupMock = vi.mocked(useHistoryEventsApi().lookupEvmTransaction);
    lookupMock.mockReset();
    lookupMock.mockResolvedValue({ taskId: 1 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should not call api when inputs are incomplete', async () => {
    const { txHash } = mount();
    set(txHash, VALID_HASH);
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();

    expect(useHistoryEventsApi().lookupEvmTransaction).not.toHaveBeenCalled();
  });

  it('should fire lookup once all inputs are valid and apply timestamp via onResolved', async () => {
    runTaskMock.mockResolvedValue({ result: createPayload(), success: true });

    const { txHash, relatedAddress, onResolved } = mount();
    set(txHash, VALID_HASH);
    set(relatedAddress, VALID_ADDRESS);
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();

    expect(onResolved).toHaveBeenCalledTimes(1);
    expect(onResolved.mock.calls[0][0].timestamp).toBe(1713350400);
  });

  it('should skip lookup when enabled is false', async () => {
    const { txHash, relatedAddress, enabled } = mount();
    set(enabled, false);
    set(txHash, VALID_HASH);
    set(relatedAddress, VALID_ADDRESS);
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();

    expect(useHistoryEventsApi().lookupEvmTransaction).not.toHaveBeenCalled();
  });

  it('should mark canRetry on actionable failure and surface message in errorMessages.txRef', async () => {
    runTaskMock.mockResolvedValue({
      backendCancelled: false,
      cancelled: false,
      message: 'Temporary rpc error',
      skipped: false,
      success: false,
    });

    const { txHash, relatedAddress, errorMessages, composable } = mount();
    set(txHash, VALID_HASH);
    set(relatedAddress, VALID_ADDRESS);
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();

    expect(get(errorMessages).txRef).toEqual(['Temporary rpc error']);
    expect(get(composable.canRetry)).toBe(true);
  });

  it('should route related_address ApiValidationError to errorFields.relatedAddress', async () => {
    const message = JSON.stringify({
      related_address: ['The address 0xabc is not tracked on ethereum in rotki'],
    });
    vi.mocked(useHistoryEventsApi().lookupEvmTransaction).mockRejectedValueOnce(
      new ApiValidationError(message),
    );

    const { txHash, relatedAddress, errorMessages, composable } = mount();
    set(txHash, VALID_HASH);
    set(relatedAddress, '0xabc');
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();

    expect(get(errorMessages).locationLabel).toEqual([
      'The address 0xabc is not tracked on ethereum in rotki',
    ]);
    expect(get(errorMessages).txRef ?? []).toEqual([]);
    expect(get(composable.canRetry)).toBe(false);
  });

  it('should cancel a previous lookup before starting a new one and discard the stale result', async () => {
    let resolveFirst: (value: unknown) => void = () => {};
    const firstResult = new Promise((resolve) => {
      resolveFirst = resolve;
    });
    runTaskMock.mockImplementationOnce(async () => firstResult);
    runTaskMock.mockResolvedValueOnce({
      result: createPayload({ timestamp: 999 }),
      success: true,
    });

    const { txHash, relatedAddress, onResolved } = mount();
    set(txHash, VALID_HASH);
    set(relatedAddress, VALID_ADDRESS);
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();

    // Trigger a second lookup while the first is still in flight.
    set(txHash, VALID_HASH_2);
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();

    expect(cancelTaskByTaskTypeMock).toHaveBeenCalledTimes(2);

    // Now resolve the older task; its result must be discarded.
    resolveFirst({ result: createPayload({ timestamp: 111 }), success: true });
    await flushPromises();

    expect(onResolved).toHaveBeenCalledTimes(1);
    expect(onResolved.mock.calls[0][0].timestamp).toBe(999);
  });

  it('should preserve unrelated errorMessages keys when writing lookup errors', async () => {
    runTaskMock.mockResolvedValue({
      backendCancelled: false,
      cancelled: false,
      message: 'boom',
      skipped: false,
      success: false,
    });

    const { txHash, relatedAddress, errorMessages } = mount();
    set(errorMessages, { amount: ['Required'] });
    set(txHash, VALID_HASH);
    set(relatedAddress, VALID_ADDRESS);
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();

    expect(get(errorMessages).amount).toEqual(['Required']);
    expect(get(errorMessages).txRef).toEqual(['boom']);
  });

  it('should clear its own errorMessages keys on reset()', async () => {
    runTaskMock.mockResolvedValue({
      backendCancelled: false,
      cancelled: false,
      message: 'boom',
      skipped: false,
      success: false,
    });

    const { txHash, relatedAddress, errorMessages, composable } = mount();
    set(txHash, VALID_HASH);
    set(relatedAddress, VALID_ADDRESS);
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();

    expect(get(errorMessages).txRef).toEqual(['boom']);

    composable.reset();
    expect(get(errorMessages).txRef).toEqual([]);
    expect(get(composable.canRetry)).toBe(false);
  });

  it('should expose needsRelatedAddress when hash+chain set but address missing', async () => {
    const { txHash, composable } = mount();
    expect(get(composable.needsRelatedAddress)).toBe(false);

    set(txHash, VALID_HASH);
    await flushPromises();
    expect(get(composable.needsRelatedAddress)).toBe(true);
  });

  it('should rewrite not-found backend message and disable retry', async () => {
    runTaskMock.mockResolvedValue({
      backendCancelled: false,
      cancelled: false,
      message: 'Unable to find transaction 0xaf at gnosis: Transaction 0xaf was not found on gnosis',
      skipped: false,
      success: false,
    });

    const { txHash, relatedAddress, evmChain, errorMessages, composable } = mount();
    set(evmChain, 'gnosis');
    set(txHash, VALID_HASH);
    set(relatedAddress, VALID_ADDRESS);
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();

    expect(get(errorMessages).txRef).toEqual(['actions.evm_tx_lookup.error.not_found::gnosis']);
    expect(get(composable.canRetry)).toBe(false);
  });

  it('retry() should re-run the lookup with current inputs', async () => {
    runTaskMock
      .mockResolvedValueOnce({
        backendCancelled: false,
        cancelled: false,
        message: 'boom',
        skipped: false,
        success: false,
      })
      .mockResolvedValueOnce({ result: createPayload({ timestamp: 100 }), success: true });

    const { txHash, relatedAddress, onResolved, composable } = mount();
    set(txHash, VALID_HASH);
    set(relatedAddress, VALID_ADDRESS);
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();
    expect(get(composable.canRetry)).toBe(true);

    await composable.retry();
    await flushPromises();

    expect(onResolved).toHaveBeenCalledTimes(1);
    expect(onResolved.mock.calls[0][0].timestamp).toBe(100);
    expect(get(composable.canRetry)).toBe(false);
  });
});
