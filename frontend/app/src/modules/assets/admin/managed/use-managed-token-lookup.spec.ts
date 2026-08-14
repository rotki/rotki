import type { Ref } from 'vue';
import { EvmTokenKind, type SupportedAsset } from '@rotki/common';
import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { EVM_TOKEN } from '@/modules/assets/types';

// Nullable on purpose: the response type declares these optional, but the backend sends null for a
// field the contract does not answer, which is what the lookup has to survive.
const fetchTokenDetails = vi.fn<(payload: { address: string; evmChain: string }) => Promise<{
  decimals?: number | null;
  name?: string | null;
  symbol?: string | null;
}>>();

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    get fetchTokenDetails() {
      return fetchTokenDetails;
    },
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    txEvmChains: computed(() => [{ evmChainName: 'ethereum' }, { evmChainName: 'optimism' }]),
  }),
}));

const { useManagedTokenLookup } = await import('@/modules/assets/admin/managed/use-managed-token-lookup');

const ADDRESS = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
const OTHER_ADDRESS = '0x6B175474E89094C44Da98b954EedeAC495271d0F';

describe('useManagedTokenLookup', () => {
  let asset: Ref<SupportedAsset>;
  let address: Ref<string>;
  let evmChain: Ref<string | undefined>;
  let filled: Array<Array<keyof SupportedAsset>>;

  function setup(): ReturnType<typeof useManagedTokenLookup> {
    return useManagedTokenLookup({
      address,
      asset,
      evmChain,
      onFilled: fields => filled.push(fields),
    });
  }

  beforeEach(() => {
    fetchTokenDetails.mockReset();
    fetchTokenDetails.mockResolvedValue({ decimals: 6, name: 'USD Coin', symbol: 'USDC' });
    filled = [];
    asset = ref<SupportedAsset>({
      address: '',
      assetType: EVM_TOKEN,
      decimals: 18,
      evmChain: 'ethereum',
      identifier: 'test-asset',
      isRebasing: false,
      name: '',
      symbol: '',
      tokenKind: EvmTokenKind.ERC20,
    });
    address = ref<string>('');
    evmChain = ref<string | undefined>('ethereum');
  });

  it('should look a token up once the address becomes a real one', async () => {
    setup();

    set(address, ADDRESS);
    await nextTick();
    await flushPromises();

    expect(fetchTokenDetails).toHaveBeenCalledWith({ address: ADDRESS, evmChain: 'ethereum' });
    expect(get(asset)).toMatchObject({ decimals: 6, name: 'USD Coin', symbol: 'USDC' });
    expect(filled).toEqual([['decimals', 'name', 'symbol']]);
  });

  it('should not look up a half-typed address', async () => {
    setup();

    set(address, '0xA0b86991');
    await nextTick();
    await flushPromises();

    expect(fetchTokenDetails).not.toHaveBeenCalled();
  });

  it('should not look up a chain that has no transaction support', async () => {
    set(evmChain, 'zksync_lite');
    setup();

    set(address, ADDRESS);
    await nextTick();
    await flushPromises();

    expect(fetchTokenDetails).not.toHaveBeenCalled();
  });

  it('should keep what the user typed for a field the contract answers with null', async () => {
    // The response type says these are optional, but the backend documents that a contract which
    // does not answer reports them as null, and a null is not what the user typed.
    fetchTokenDetails.mockResolvedValue({ decimals: null, name: null, symbol: null });
    set(asset, { ...get(asset), decimals: 8, name: 'My own name', symbol: 'MINE' });
    setup();

    set(address, ADDRESS);
    await nextTick();
    await flushPromises();

    expect(get(asset)).toMatchObject({ decimals: 8, name: 'My own name', symbol: 'MINE' });
  });

  it('should keep what the user typed for a field the chain has nothing for', async () => {
    fetchTokenDetails.mockResolvedValue({ symbol: 'USDC' });
    set(asset, { ...get(asset), decimals: 8, name: 'My own name' });
    setup();

    set(address, ADDRESS);
    await nextTick();
    await flushPromises();

    expect(get(asset)).toMatchObject({ decimals: 8, name: 'My own name', symbol: 'USDC' });
  });

  it('should skip exactly one lookup when told to', async () => {
    const { suppressNextLookup } = setup();
    suppressNextLookup();

    set(address, ADDRESS);
    await nextTick();
    await flushPromises();
    expect(fetchTokenDetails).not.toHaveBeenCalled();

    set(address, OTHER_ADDRESS);
    await nextTick();
    await flushPromises();
    expect(fetchTokenDetails).toHaveBeenCalledTimes(1);
  });

  it('should report it is fetching while the lookup runs', async () => {
    let release: (value: { symbol: string }) => void = () => {};
    fetchTokenDetails.mockReturnValue(new Promise((resolve) => {
      release = resolve;
    }));
    const { fetching } = setup();

    set(address, ADDRESS);
    await nextTick();
    expect(get(fetching)).toBe(true);

    release({ symbol: 'USDC' });
    await flushPromises();
    expect(get(fetching)).toBe(false);
  });

  it('should stop fetching even when the lookup throws', async () => {
    fetchTokenDetails.mockRejectedValue(new Error('no such token'));
    const { fetching, refreshTokenData } = setup();

    await expect(refreshTokenData()).rejects.toThrow('no such token');

    expect(get(fetching)).toBe(false);
  });

  it('should look up on request without waiting for an edit', async () => {
    set(address, ADDRESS);
    const { refreshTokenData } = setup();

    await refreshTokenData();

    expect(fetchTokenDetails).toHaveBeenCalledWith({ address: ADDRESS, evmChain: 'ethereum' });
  });

  it('should do nothing on request when no chain is chosen', async () => {
    set(evmChain, undefined);
    const { refreshTokenData } = setup();

    await refreshTokenData();

    expect(fetchTokenDetails).not.toHaveBeenCalled();
  });

  it('should keep an edit made while the lookup was in flight', async () => {
    let release: (value: { symbol: string }) => void = () => {};
    fetchTokenDetails.mockReturnValue(new Promise((resolve) => {
      release = resolve;
    }));
    setup();

    set(address, ADDRESS);
    await nextTick();
    set(asset, { ...get(asset), name: 'Typed while waiting' });

    release({ symbol: 'USDC' });
    await flushPromises();

    expect(get(asset).name).toBe('Typed while waiting');
  });
});
