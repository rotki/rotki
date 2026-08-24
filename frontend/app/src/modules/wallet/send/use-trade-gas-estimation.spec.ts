import type { EffectScope, Ref } from 'vue';
import type { GasFeeEstimation } from '@/modules/wallet/types';
import flushPromises from 'flush-promises';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTradeGasEstimation } from '@/modules/wallet/send/use-trade-gas-estimation';

const ETHEREUM_CHAIN_ID = 1;
const OPTIMISM_CHAIN_ID = 10;
const CHAIN_IDS: Record<string, number | undefined> = {
  eth: ETHEREUM_CHAIN_ID,
  optimism: OPTIMISM_CHAIN_ID,
};

const connected = ref<boolean>(true);
const connectedChainId = ref<number>();
const getGasFeeForChain = vi.fn<() => Promise<GasFeeEstimation>>();

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: vi.fn(() => ({ connected, connectedChainId, getGasFeeForChain })),
}));

// The chain refs carry rotki blockchain ids (`eth`), which is what the send form
// binds; an unknown chain resolves to no numeric id, as the real helper does.
vi.mock('@/modules/wallet/use-wallet-helper', () => ({
  useWalletHelper: vi.fn(() => ({
    getChainIdFromChain: (chain: string): number | undefined => CHAIN_IDS[chain],
  })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

/** A gas estimate the test resolves by hand, to hold a request open across other changes. */
function deferred(): { promise: Promise<GasFeeEstimation>; resolve: (gasFee: string) => void } {
  let resolve: (value: GasFeeEstimation) => void;
  const promise = new Promise<GasFeeEstimation>((res) => {
    resolve = res;
  });
  return { promise, resolve: (gasFee: string): void => resolve({ gasFee, maxAmount: '0' }) };
}

describe('useTradeGasEstimation', () => {
  let scope: EffectScope;
  let asset: Ref<string>;
  let chain: Ref<string>;
  let isNativeAsset: Ref<boolean>;
  let isAssetResolved: Ref<boolean>;

  function create(): ReturnType<typeof useTradeGasEstimation> {
    scope = effectScope();
    const result = scope.run(() => useTradeGasEstimation({ asset, chain, isAssetResolved, isNativeAsset }));
    assert(result);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(connected, true);
    set(connectedChainId, ETHEREUM_CHAIN_ID);
    asset = ref<string>('ETH');
    chain = ref<string>('eth');
    isNativeAsset = ref<boolean>(true);
    isAssetResolved = ref<boolean>(true);
    getGasFeeForChain.mockResolvedValue({ gasFee: '0.01', maxAmount: '0' });
  });

  afterEach(() => {
    scope.stop();
  });

  it('should estimate for a native asset on the connected chain', async () => {
    const { estimatedGasFee } = create();
    await flushPromises();

    expect(getGasFeeForChain).toHaveBeenCalledOnce();
    expect(get(estimatedGasFee)).toBe('0.01');
  });

  it('should not estimate while no wallet is connected', async () => {
    set(connected, false);
    const { estimatedGasFee, gasEstimable } = create();
    await flushPromises();

    expect(get(gasEstimable)).toBe(false);
    expect(getGasFeeForChain).not.toHaveBeenCalled();
    expect(get(estimatedGasFee)).toBe('0');
  });

  it('should not estimate until the asset resolves', async () => {
    set(isAssetResolved, false);
    const { gasEstimable } = create();
    await flushPromises();

    expect(get(gasEstimable)).toBe(false);
    expect(getGasFeeForChain).not.toHaveBeenCalled();
  });

  it('should charge no gas for a non-native asset', async () => {
    set(isNativeAsset, false);
    const { estimatedGasFee } = create();
    await flushPromises();

    expect(getGasFeeForChain).not.toHaveBeenCalled();
    expect(get(estimatedGasFee)).toBe('0');
  });

  it('should charge no gas while the wallet is on another chain', async () => {
    set(connectedChainId, OPTIMISM_CHAIN_ID);
    const { estimatedGasFee } = create();
    await flushPromises();

    expect(getGasFeeForChain).not.toHaveBeenCalled();
    expect(get(estimatedGasFee)).toBe('0');
  });

  it('should charge no gas when the selected chain has no numeric id', async () => {
    // Both sides of the chain comparison are undefined here: the chain cannot be
    // resolved and the wallet has reported no chain. That is not a match.
    set(chain, 'newchain');
    set(connectedChainId, undefined);
    const { estimatedGasFee } = create();
    await flushPromises();

    expect(getGasFeeForChain).not.toHaveBeenCalled();
    expect(get(estimatedGasFee)).toBe('0');
  });

  it('should report that it is estimating while a request is in flight', async () => {
    const pending = deferred();
    getGasFeeForChain.mockReturnValue(pending.promise);
    const { estimatedGasFee, estimatingGas } = create();
    await nextTick();

    expect(get(estimatingGas)).toBe(true);

    pending.resolve('0.02');
    await flushPromises();

    expect(get(estimatingGas)).toBe(false);
    expect(get(estimatedGasFee)).toBe('0.02');
  });

  it('should drop an estimate that resolves after the asset changed', async () => {
    const pending = deferred();
    getGasFeeForChain.mockReturnValueOnce(pending.promise);
    const { estimatedGasFee } = create();
    await nextTick();

    // Clearing the asset makes the next run bail before it aborts anything, so the first request
    // is still live when it resolves - only the stale-asset check can discard it.
    set(asset, '');
    await nextTick();
    pending.resolve('99');
    await flushPromises();

    expect(get(estimatedGasFee)).toBe('0');
  });

  it('should abort the previous request when the selection changes', async () => {
    const pending = deferred();
    getGasFeeForChain.mockReturnValueOnce(pending.promise);
    const { estimatedGasFee } = create();
    await nextTick();

    getGasFeeForChain.mockResolvedValue({ gasFee: '0.05', maxAmount: '0' });
    set(asset, 'DAI');
    await flushPromises();

    // The aborted request rejects, and that rejection must not clear the newer estimate.
    pending.resolve('99');
    await flushPromises();

    expect(get(estimatedGasFee)).toBe('0.05');
    expect(getGasFeeForChain).toHaveBeenCalledTimes(2);
  });

  it('should reset the fee when the estimate fails', async () => {
    getGasFeeForChain.mockRejectedValue(new Error('rpc is down'));
    const { estimatedGasFee } = create();
    await flushPromises();

    expect(get(estimatedGasFee)).toBe('0');
  });

  it('should re-estimate when the connected chain changes', async () => {
    create();
    await flushPromises();
    expect(getGasFeeForChain).toHaveBeenCalledOnce();

    set(chain, 'optimism');
    set(connectedChainId, OPTIMISM_CHAIN_ID);
    await flushPromises();

    expect(getGasFeeForChain).toHaveBeenCalledTimes(2);
  });
});
