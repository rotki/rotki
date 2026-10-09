import type { AssetInfoWithId } from '@rotki/common';
import { flushPromises, mount } from '@vue/test-utils';
import { get, set } from '@vueuse/core';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, ref, type Ref } from 'vue';
import { useAssetSearch } from '@/modules/shell/components/inputs/use-asset-search';

const EVM_CHAIN_BY_ID: Record<string, string> = { arbitrum_one: 'arbitrum', eth: 'ethereum' };

const mockAssetSearch = vi.fn();
const mockAssetMapping = vi.fn();
const mockIsAssetIgnored = vi.fn();

vi.mock('@/modules/assets/api/use-asset-info-api', () => ({
  useAssetInfoApi: (): object => ({
    assetMapping: mockAssetMapping,
    assetSearch: mockAssetSearch,
  }),
}));

vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: (): object => ({
    isAssetIgnored: mockIsAssetIgnored,
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    getEvmChainName: (chain: string): string | undefined => EVM_CHAIN_BY_ID[chain],
    matchChain: (chain: string): string | undefined => EVM_CHAIN_BY_ID[chain] ? chain : undefined,
  }),
}));

function makeAsset(identifier: string): AssetInfoWithId {
  return { assetType: 'evm token', identifier, name: 'USD Coin', symbol: 'USDC' };
}

interface Harness {
  api: ReturnType<typeof useAssetSearch>;
  chain: Ref<string | undefined>;
  items: Ref<string[]>;
  modelValue: Ref<string | undefined>;
  nftHandling: Ref<'exclude' | 'include' | 'show_only'>;
  selectionLost: ReturnType<typeof vi.fn>;
}

function setup(opts: {
  modelValue?: string;
  chain?: string;
  showIgnored?: boolean;
  excludes?: string[];
  items?: string[];
  nftHandling?: 'exclude' | 'include' | 'show_only';
} = {}): Harness {
  const modelValue = ref<string | undefined>(opts.modelValue);
  const chain = ref<string | undefined>(opts.chain);
  const items = ref<string[]>(opts.items ?? []);
  const nftHandling = ref<'exclude' | 'include' | 'show_only'>(opts.nftHandling ?? 'exclude');
  const selectionLost = vi.fn();
  let api!: ReturnType<typeof useAssetSearch>;
  mount(defineComponent({
    setup() {
      api = useAssetSearch({
        chain,
        excludes: () => opts.excludes ?? [],
        nftHandling: () => get(nftHandling),
        items: () => get(items),
        modelValue,
        onSelectionLost: selectionLost,
        showIgnored: () => opts.showIgnored ?? false,
      });
      return (): null => null;
    },
  }));
  return { api, chain, items, modelValue, nftHandling, selectionLost };
}

const OWNED: Record<string, { name: string; symbol: string }> = {
  'BTC': { name: 'Bitcoin', symbol: 'BTC' },
  'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': { name: 'USD Coin', symbol: 'USDC' },
  'ETH': { name: 'Ethereum', symbol: 'ETH' },
};

const USDC = 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';

/** Answers a mapping request the way colibri does: only the identifiers it knows. */
function mapKnownAssets(identifiers: string[]): object {
  return {
    assetCollections: {},
    assets: Object.fromEntries(identifiers.filter(id => OWNED[id]).map(id => [id, { assetType: 'own chain', ...OWNED[id] }])),
  };
}

function identifiersOf(api: ReturnType<typeof useAssetSearch>): string[] {
  return get(api.visibleAssets).map(asset => asset.identifier);
}

async function runSearch(api: ReturnType<typeof useAssetSearch>, term: string): Promise<void> {
  set(api.modelSearch, term);
  await vi.advanceTimersByTimeAsync(800);
  await flushPromises();
}

describe('useAssetSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockAssetSearch.mockReset();
    mockAssetMapping.mockReset();
    mockAssetMapping.mockResolvedValue({ assets: {} });
    mockIsAssetIgnored.mockReset();
    mockIsAssetIgnored.mockReturnValue(false);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should populate the options from a chain-scoped search', async () => {
    mockAssetSearch.mockResolvedValue([makeAsset('eip155:1/erc20:0xA')]);
    const { api } = setup({ chain: 'eth' });

    await runSearch(api, 'usdc');

    expect(mockAssetSearch).toHaveBeenCalledWith(expect.objectContaining({ evmChain: 'ethereum' }));
    expect(get(api.visibleAssets)).toHaveLength(1);
  });

  it('should hide ignored assets unless they are the selected value', async () => {
    mockAssetSearch.mockResolvedValue([makeAsset('A'), makeAsset('B')]);
    mockIsAssetIgnored.mockImplementation((id: string) => id === 'B');

    const hidden = setup({});
    await runSearch(hidden.api, 'x');
    expect(get(hidden.api.visibleAssets).map(a => a.identifier)).toStrictEqual(['A']);

    const selected = setup({ modelValue: 'B' });
    await runSearch(selected.api, 'x');
    expect(get(selected.api.visibleAssets).map(a => a.identifier)).toContain('B');
  });

  it('should drop cached options when the chain changes and nothing is selected', async () => {
    mockAssetSearch.mockResolvedValue([makeAsset('eip155:1/erc20:0xA')]);
    const { api, chain } = setup({ chain: 'eth' });
    await runSearch(api, 'usdc');
    expect(get(api.visibleAssets)).toHaveLength(1);

    set(chain, 'arbitrum_one');
    await flushPromises();

    expect(get(api.visibleAssets)).toHaveLength(0);
  });

  it('should retain the selected asset in the options when the chain changes', async () => {
    const { chain } = setup({ modelValue: 'eip155:1/erc20:0xA' });
    mockAssetMapping.mockClear();

    set(chain, 'arbitrum_one');
    await flushPromises();

    expect(mockAssetMapping).toHaveBeenCalledWith(['eip155:1/erc20:0xA']);
  });

  it('should drop the options when the nft handling changes', async () => {
    mockAssetSearch.mockResolvedValue([makeAsset('eip155:1/erc20:0xA')]);
    const { api, nftHandling } = setup();
    await runSearch(api, 'usdc');
    expect(get(api.visibleAssets)).toHaveLength(1);

    set(nftHandling, 'show_only');
    await flushPromises();

    expect(get(api.visibleAssets)).toHaveLength(0);
  });

  it('should give up a selection the new nft handling cannot offer', async () => {
    const { modelValue, nftHandling, selectionLost } = setup({ modelValue: 'eip155:1/erc20:0xA' });

    set(nftHandling, 'show_only');
    await flushPromises();

    expect(selectionLost).toHaveBeenCalled();
    expect(modelValue).toBeDefined();
  });

  it('should discard a response that resolved before the nft handling changed, which aborting alone cannot catch', async () => {
    let resolveSearch!: (assets: AssetInfoWithId[]) => void;
    mockAssetSearch.mockReturnValue(new Promise((resolve) => {
      resolveSearch = resolve;
    }));
    const { api, nftHandling } = setup();

    set(api.modelSearch, 'usdc');
    await vi.advanceTimersByTimeAsync(800);

    set(nftHandling, 'show_only');
    await flushPromises();

    // The token search now answers, for a scope nobody is looking at any more.
    resolveSearch([makeAsset('eip155:1/erc20:0xA')]);
    await flushPromises();

    expect(get(api.visibleAssets)).toHaveLength(0);
  });

  it('should keep a selection the new nft handling still admits', async () => {
    const { nftHandling, selectionLost } = setup({
      modelValue: '_nft_0xc3f733ca98E0daD0386979Eb96fb1722A1A05E69_129',
      nftHandling: 'show_only',
    });

    set(nftHandling, 'include');
    await flushPromises();

    expect(selectionLost).not.toHaveBeenCalled();
  });

  // The statistics graph passes the user's own assets; the picker must be a closed list of them.
  describe('with an allow-list', () => {
    beforeEach(() => {
      mockAssetMapping.mockImplementation(async (ids: string[]) => mapKnownAssets(ids));
    });

    it('should offer every listed asset before anything is typed, in the given order', async () => {
      const { api } = setup({ items: ['ETH', USDC, 'BTC'] });
      await flushPromises();

      expect(identifiersOf(api)).toStrictEqual(['ETH', USDC, 'BTC']);
      expect(get(api.visibleAssets)[1]).toMatchObject({ name: 'USD Coin', symbol: 'USDC' });
      expect(mockAssetSearch).not.toHaveBeenCalled();
    });

    it('should filter locally by symbol, name and identifier', async () => {
      const { api } = setup({ items: ['ETH', USDC, 'BTC'] });
      await flushPromises();

      await runSearch(api, 'usd');
      expect(identifiersOf(api)).toStrictEqual([USDC]);

      await runSearch(api, 'bitco');
      expect(identifiersOf(api)).toStrictEqual(['BTC']);

      await runSearch(api, '0xa0b8');
      expect(identifiersOf(api)).toStrictEqual([USDC]);

      await runSearch(api, '');
      expect(identifiersOf(api)).toStrictEqual(['ETH', USDC, 'BTC']);
      expect(mockAssetSearch).not.toHaveBeenCalled();
    });

    // The reported bug: 50 global results for `u` pushed the user's own USDC out.
    it('should offer an owned asset that a 50-result global search would leave out', async () => {
      mockAssetSearch.mockResolvedValue(Array.from({ length: 50 }, (_, index) => makeAsset(`eip155:1/erc20:0x${index}`)));
      const { api } = setup({ items: ['ETH', USDC] });
      await flushPromises();

      await runSearch(api, 'u');

      expect(identifiersOf(api)).toContain(USDC);
      expect(mockAssetSearch).not.toHaveBeenCalled();
    });

    it('should open on the top 20 of a long list and reach the rest by typing', async () => {
      const items = Array.from({ length: 120 }, (_, index) => `ASSET${index}`);
      const { api } = setup({ items });
      await flushPromises();

      expect(mockAssetMapping).toHaveBeenCalledTimes(3);
      expect(identifiersOf(api)).toStrictEqual(items.slice(0, 20));

      await runSearch(api, 'asset119');
      expect(identifiersOf(api)).toStrictEqual(['ASSET119']);
    });

    it('should keep a selection ranked below the open list', async () => {
      const items = Array.from({ length: 30 }, (_, index) => `ASSET${index}`);
      const { api } = setup({ items, modelValue: 'ASSET25' });
      await flushPromises();

      expect(identifiersOf(api)).toStrictEqual([...items.slice(0, 20), 'ASSET25']);
    });

    // The first batch holds the top of the ranking, so the list must not wait on the rest.
    it('should offer the first batch before the rest has resolved', async () => {
      let resolveRest!: () => void;
      const rest = new Promise<void>((resolve) => {
        resolveRest = resolve;
      });
      mockAssetMapping.mockImplementation(async (ids: string[]) => {
        if (ids[0] !== 'ASSET0')
          await rest;
        return mapKnownAssets(ids);
      });
      const items = Array.from({ length: 60 }, (_, index) => `ASSET${index}`);
      const { api } = setup({ items });
      await flushPromises();

      expect(identifiersOf(api)).toStrictEqual(items.slice(0, 20));
      expect(get(api.loading)).toBe(true);

      resolveRest();
      await flushPromises();
      expect(get(api.loading)).toBe(false);
    });

    it('should keep the selected asset while the filter excludes it', async () => {
      const { api, selectionLost } = setup({ items: ['ETH', USDC], modelValue: 'ETH' });
      await flushPromises();

      await runSearch(api, 'usdc');

      expect(identifiersOf(api)).toStrictEqual(['ETH', USDC]);
      expect(selectionLost).not.toHaveBeenCalled();
    });

    it('should re-resolve when the list changes and give up a selection that left it', async () => {
      const { api, items, selectionLost } = setup({ items: ['ETH', USDC], modelValue: 'ETH' });
      await flushPromises();

      set(items, [USDC, 'BTC']);
      await flushPromises();

      expect(identifiersOf(api)).toStrictEqual([USDC, 'BTC']);
      expect(selectionLost).toHaveBeenCalled();
    });

    it('should not re-resolve when the list is replaced with the same contents', async () => {
      const { items } = setup({ items: ['ETH', USDC] });
      await flushPromises();
      mockAssetMapping.mockClear();

      set(items, ['ETH', USDC]);
      await flushPromises();

      expect(mockAssetMapping).not.toHaveBeenCalled();
    });

    it('should go back to the remote search when the list is emptied', async () => {
      mockAssetSearch.mockResolvedValue([makeAsset('eip155:1/erc20:0xA')]);
      const { api, items } = setup({ items: ['ETH'] });
      await flushPromises();

      set(items, []);
      await flushPromises();
      await runSearch(api, 'usdc');

      expect(mockAssetSearch).toHaveBeenCalled();
      expect(identifiersOf(api)).toStrictEqual(['eip155:1/erc20:0xA']);
    });
  });
});
