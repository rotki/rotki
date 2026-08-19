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

  it('should react to the search changing', () => {
    const search = ref<string>('');
    const assets = [asset('eip155:1/erc20:0xccc', 'eth'), asset('eip155:1/erc20:0xbbb', 'eth')];

    const { options } = useTradeAssetOptions(assets, 'eth', search, ['eth']);
    expect(get(options)).toHaveLength(2);

    set(search, 'age');
    expect(get(options).map(option => option.symbol)).toEqual(['AGE']);
  });
});
