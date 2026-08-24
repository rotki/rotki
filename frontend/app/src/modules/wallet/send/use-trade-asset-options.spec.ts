import type { TradableAsset } from '@/modules/wallet/types';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ALL_CHAINS, useTradeAssetOptions } from './use-trade-asset-options';

const getAssetField = vi.fn<(identifier: string, field: string) => string>();
const getNativeAsset = vi.fn<(chain: string) => string>();

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({ getAssetField })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getNativeAsset })),
}));

const NAMES: Record<string, { symbol: string; name: string }> = {
  'ETH': { name: 'Ethereum', symbol: 'ETH' },
  'eip155:1/erc20:0xaaa': { name: 'Zeus Finance', symbol: 'ZEU' },
  'eip155:1/erc20:0xbbb': { name: 'AgentX', symbol: 'AGE' },
  'eip155:1/erc20:0xccc': { name: 'TrueUSD', symbol: 'TUSD' },
  'eip155:10/erc20:0xddd': { name: 'Optimism Token', symbol: 'OPT' },
};

function asset(identifier: string, chain: string, fiatValue?: string): TradableAsset {
  return {
    amount: bigNumberify(1),
    asset: identifier,
    chain,
    fiatValue: fiatValue ? bigNumberify(fiatValue) : undefined,
  };
}

describe('useTradeAssetOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getNativeAsset.mockImplementation((chain: string) => (chain === 'eth' ? 'ETH' : 'OP'));
    getAssetField.mockImplementation((identifier: string, field: string) => {
      const entry = NAMES[identifier];
      if (!entry)
        return '';
      return field === 'symbol' ? entry.symbol : entry.name;
    });
  });

  it('should order an unpriced list alphabetically by symbol, native first', () => {
    const assets = [
      asset('eip155:1/erc20:0xaaa', 'eth'),
      asset('eip155:1/erc20:0xbbb', 'eth'),
      asset('ETH', 'eth'),
      asset('eip155:1/erc20:0xccc', 'eth'),
    ];

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth']);

    expect(get(options).map(option => option.symbol)).toEqual(['ETH', 'AGE', 'TUSD', 'ZEU']);
  });

  it('should keep fiat value ahead of the symbol ordering', () => {
    const assets = [
      asset('eip155:1/erc20:0xbbb', 'eth', '5'),
      asset('eip155:1/erc20:0xccc', 'eth', '100'),
      asset('eip155:1/erc20:0xaaa', 'eth', '50'),
    ];

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth']);

    expect(get(options).map(option => option.symbol)).toEqual(['TUSD', 'ZEU', 'AGE']);
  });

  it('should fall back to the identifier when a symbol has not resolved yet', () => {
    getAssetField.mockReturnValue('');
    const assets = [asset('eip155:1/erc20:0xbbb', 'eth'), asset('eip155:1/erc20:0xaaa', 'eth')];

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth']);

    expect(get(options).map(option => option.asset.asset)).toEqual([
      'eip155:1/erc20:0xaaa',
      'eip155:1/erc20:0xbbb',
    ]);
  });

  it('should narrow to the selected chain', () => {
    const assets = [asset('ETH', 'eth'), asset('eip155:10/erc20:0xddd', 'optimism')];

    const { options } = useTradeAssetOptions(assets, 'optimism', '', ['eth', 'optimism']);

    expect(get(options).map(option => option.symbol)).toEqual(['OPT']);
  });

  it('should keep every supported chain when the chain is "all"', () => {
    const assets = [
      asset('ETH', 'eth'),
      asset('eip155:10/erc20:0xddd', 'optimism'),
      asset('eip155:1/erc20:0xaaa', 'gnosis'),
    ];

    const { options } = useTradeAssetOptions(assets, ALL_CHAINS, '', ['eth', 'optimism']);

    expect(get(options).map(option => option.symbol)).toEqual(['ETH', 'OPT']);
  });

  it('should match the search against the symbol', () => {
    const assets = [asset('eip155:1/erc20:0xccc', 'eth'), asset('eip155:1/erc20:0xbbb', 'eth')];

    const { options } = useTradeAssetOptions(assets, 'eth', 'tus', ['eth']);

    expect(get(options).map(option => option.symbol)).toEqual(['TUSD']);
  });

  it('should match the search against the name, case insensitively', () => {
    const assets = [asset('eip155:1/erc20:0xaaa', 'eth'), asset('eip155:1/erc20:0xbbb', 'eth')];

    const { options } = useTradeAssetOptions(assets, 'eth', 'ZEUS fin', ['eth']);

    expect(get(options).map(option => option.symbol)).toEqual(['ZEU']);
  });

  it('should match the search against the identifier so an address finds its token', () => {
    const assets = [asset('eip155:1/erc20:0xaaa', 'eth'), asset('eip155:1/erc20:0xbbb', 'eth')];

    const { options } = useTradeAssetOptions(assets, 'eth', '0xBBB', ['eth']);

    expect(get(options).map(option => option.symbol)).toEqual(['AGE']);
  });

  it('should return an empty list when nothing matches the search', () => {
    const assets = [asset('eip155:1/erc20:0xaaa', 'eth')];

    const { options } = useTradeAssetOptions(assets, 'eth', 'nothingmatchesthis', ['eth']);

    expect(get(options)).toEqual([]);
  });

  it('should resolve each asset once rather than once per field read', () => {
    const assets = [asset('ETH', 'eth'), asset('eip155:1/erc20:0xaaa', 'eth')];

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth']);
    get(options);
    get(options);

    // two assets, symbol + name each, and the computed is cached across reads
    expect(getAssetField).toHaveBeenCalledTimes(4);
  });

  it('should drop collectibles, which this form cannot send', () => {
    const assets = [
      asset('ETH', 'eth'),
      asset('eip155:1/erc721:0xC0a302e6Ad8EcCC4d7A6c1514F8671D6B79269c7/104', 'eth'),
      asset('eip155:1/erc1155:0xC0a302e6Ad8EcCC4d7A6c1514F8671D6B79269c7/7', 'eth'),
      asset('_nft_0xC0a302e6Ad8EcCC4d7A6c1514F8671D6B79269c7_104', 'eth'),
    ];

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth']);

    expect(get(options).map(option => option.asset.asset)).toEqual(['ETH']);
  });

  it('should flag a symbol that another row on the chain also uses', () => {
    getAssetField.mockImplementation((_identifier: string, field: string) =>
      field === 'symbol' ? 'ASK' : 'GoAsk');
    const assets = [
      asset('eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 'eth'),
      asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', 'eth'),
    ];

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth']);

    const flagged = get(options);
    expect(flagged.every(option => option.ambiguous)).toBe(true);
    expect(flagged.map(option => option.address)).toEqual(['0x1f98…F984', '0x6B17…1d0F']);
  });

  it('should not flag a symbol that is unique on the chain', () => {
    const assets = [asset('eip155:1/erc20:0xaaa', 'eth'), asset('eip155:1/erc20:0xbbb', 'eth')];

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth']);

    expect(get(options).every(option => !option.ambiguous)).toBe(true);
  });

  it('should judge ambiguity per chain rather than across the whole holding', () => {
    getAssetField.mockImplementation((_identifier: string, field: string) =>
      field === 'symbol' ? 'USDC' : 'USD Coin');
    const assets = [
      asset('eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 'eth'),
      asset('eip155:10/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', 'optimism'),
    ];

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth', 'optimism']);

    // One USDC on this chain: the other lives on optimism and is not on screen beside it.
    expect(get(options).every(option => !option.ambiguous)).toBe(true);
  });

  it('should not flag unresolved assets as sharing a symbol', () => {
    // Everything is unresolved on first open, so every symbol is ''. Counting those together would
    // mark the whole list ambiguous and print an address beside a blank symbol on every row.
    getAssetField.mockReturnValue('');
    const assets = [
      asset('eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 'eth'),
      asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', 'eth'),
    ];

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth']);

    expect(get(options).every(option => !option.ambiguous)).toBe(true);
  });

  it('should resolve nothing until the caller opens the gate', () => {
    const assets = [asset('ETH', 'eth'), asset('eip155:1/erc20:0xaaa', 'eth')];
    const resolveNames = ref<boolean>(false);

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth'], resolveNames);
    expect(get(options)).toHaveLength(2);
    // getAssetField resolves through a cache that queues a backend fetch for anything it lacks, so
    // touching it before the dialog opens costs a mapping request for the whole holding.
    expect(getAssetField).not.toHaveBeenCalled();
    expect(get(options).every(option => option.symbol === '')).toBe(true);

    set(resolveNames, true);

    // Read first: the computed is lazy, so asserting before touching it would only prove that
    // nothing had re-evaluated yet.
    expect(get(options)[0].symbol).toBe('ETH');
    expect(getAssetField).toHaveBeenCalled();
  });

  it('should still order without symbols while the gate is closed', () => {
    const assets = [asset('eip155:1/erc20:0xbbb', 'eth'), asset('ETH', 'eth')];

    const { options } = useTradeAssetOptions(assets, 'eth', '', ['eth'], false);

    // Native first still holds; the rest falls back to the identifier, which needs no resolution.
    expect(get(options).map(option => option.asset.asset)).toEqual(['ETH', 'eip155:1/erc20:0xbbb']);
  });

  it('should expose the full ordered list unnarrowed by chain or search', () => {
    const assets = [
      asset('eip155:10/erc20:0xddd', 'optimism'),
      asset('ETH', 'eth'),
      asset('eip155:1/erc20:0xaaa', 'eth'),
    ];

    const { orderedAssets } = useTradeAssetOptions(assets, 'eth', 'tus', ['eth']);

    expect(get(orderedAssets)).toHaveLength(3);
    expect(get(orderedAssets)[0].asset.asset).toBe('ETH');
  });

  it('should react to the search changing', () => {
    const search = ref<string>('');
    const assets = [asset('eip155:1/erc20:0xccc', 'eth'), asset('eip155:1/erc20:0xbbb', 'eth')];

    const { options } = useTradeAssetOptions(assets, 'eth', search, ['eth']);
    expect(get(options)).toHaveLength(2);

    set(search, 'age');
    expect(get(options).map(option => option.symbol)).toEqual(['AGE']);
  });
});
