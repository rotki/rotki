import type { EffectScope, Ref } from 'vue';
import type { GetAssetBalancePayload } from '@/modules/wallet/types';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { neverSettles } from '@test/utils/never-settles';
import flushPromises from 'flush-promises';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTradeAssetBalance } from '@/modules/wallet/send/use-trade-asset-balance';

const getAssetBalance = vi.fn<(payload: GetAssetBalancePayload) => Promise<BigNumber>>();

vi.mock('@/modules/wallet/send/use-trade-api', () => ({
  useTradeApi: vi.fn(() => ({ getAssetBalance })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getEvmChainName: (chain: string): string | undefined => (chain === 'unsupported' ? undefined : chain),
  })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

describe('useTradeAssetBalance', () => {
  let scope: EffectScope;
  let asset: Ref<string>;
  let chain: Ref<string>;
  let address: Ref<string | undefined>;
  let amount: Ref<string>;
  let estimatedGasFee: Ref<string>;
  let gasEstimable: Ref<boolean>;

  function create(): ReturnType<typeof useTradeAssetBalance> {
    scope = effectScope();
    const result = scope.run(() =>
      useTradeAssetBalance({ address, amount, asset, chain, estimatedGasFee, gasEstimable }),
    );
    assert(result);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    asset = ref<string>('ETH');
    chain = ref<string>('ethereum');
    address = ref<string | undefined>('0x9531C059098e3d194fF87FebB587aB07B30B1306');
    amount = ref<string>('');
    estimatedGasFee = ref<string>('0');
    gasEstimable = ref<boolean>(true);
    getAssetBalance.mockResolvedValue(bigNumberify('2'));
  });

  afterEach(() => {
    scope.stop();
  });

  it('should read the balance for the current asset, chain and address', async () => {
    const { assetBalance, refreshAssetBalance } = create();
    await refreshAssetBalance();

    expect(getAssetBalance).toHaveBeenCalledWith({
      address: '0x9531C059098e3d194fF87FebB587aB07B30B1306',
      asset: 'ETH',
      evmChain: 'ethereum',
    });
    expect(get(assetBalance)?.toFixed()).toBe('2');
  });

  it('should clear the entered amount on every refresh', async () => {
    const { refreshAssetBalance } = create();
    set(amount, '1.5');

    await refreshAssetBalance();

    expect(get(amount)).toBe('');
  });

  it('should not query without an address', async () => {
    set(address, undefined);
    const { assetBalance, refreshAssetBalance } = create();
    await refreshAssetBalance();

    expect(getAssetBalance).not.toHaveBeenCalled();
    expect(get(assetBalance)).toBeUndefined();
  });

  it('should not query a chain with no evm name', async () => {
    set(chain, 'unsupported');
    const { refreshAssetBalance } = create();
    await refreshAssetBalance();

    expect(getAssetBalance).not.toHaveBeenCalled();
  });

  it('should keep the balance undefined when the query fails', async () => {
    getAssetBalance.mockRejectedValue(new Error('backend is down'));
    const { assetBalance, refreshAssetBalance } = create();
    await refreshAssetBalance();

    expect(get(assetBalance)).toBeUndefined();
  });

  it('should drop a balance that arrives after the asset changed', async () => {
    let resolve: (value: BigNumber) => void;
    getAssetBalance
      .mockReturnValueOnce(new Promise<BigNumber>((res) => {
        resolve = res;
      }))
      .mockReturnValue(neverSettles<BigNumber>());
    const { assetBalance, refreshAssetBalance } = create();
    const pending = refreshAssetBalance();

    set(asset, 'DAI');
    resolve!(bigNumberify('99'));
    await pending;

    expect(get(assetBalance)).toBeUndefined();
  });

  it('should refresh when the asset changes', async () => {
    create();
    await flushPromises();
    expect(getAssetBalance).not.toHaveBeenCalled();

    set(asset, 'DAI');
    await flushPromises();

    expect(getAssetBalance).toHaveBeenCalledOnce();
  });

  it('should hold back the gas fee from the sendable max', async () => {
    const { max, refreshAssetBalance } = create();
    set(estimatedGasFee, '0.25');
    await refreshAssetBalance();
    await nextTick();

    expect(get(max)).toBe('1.75');
  });

  it('should offer no max while gas cannot be estimated', async () => {
    const { max, refreshAssetBalance } = create();
    await refreshAssetBalance();
    await nextTick();
    expect(get(max)).toBe('2');

    set(gasEstimable, false);
    await nextTick();

    expect(get(max)).toBe('0');
  });
});
