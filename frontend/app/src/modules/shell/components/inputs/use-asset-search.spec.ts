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
  modelValue: Ref<string | undefined>;
  nftHandling: Ref<'exclude' | 'include' | 'show_only'>;
  selectionLost: ReturnType<typeof vi.fn>;
}

function setup(opts: {
  modelValue?: string;
  chain?: string;
  showIgnored?: boolean;
  excludes?: string[];
  nftHandling?: 'exclude' | 'include' | 'show_only';
} = {}): Harness {
  const modelValue = ref<string | undefined>(opts.modelValue);
  const chain = ref<string | undefined>(opts.chain);
  const nftHandling = ref<'exclude' | 'include' | 'show_only'>(opts.nftHandling ?? 'exclude');
  const selectionLost = vi.fn();
  let api!: ReturnType<typeof useAssetSearch>;
  mount(defineComponent({
    setup() {
      api = useAssetSearch({
        chain,
        excludes: () => opts.excludes ?? [],
        nftHandling: () => get(nftHandling),
        items: () => [],
        modelValue,
        onSelectionLost: selectionLost,
        showIgnored: () => opts.showIgnored ?? false,
      });
      return (): null => null;
    },
  }));
  return { api, chain, modelValue, nftHandling, selectionLost };
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
});
