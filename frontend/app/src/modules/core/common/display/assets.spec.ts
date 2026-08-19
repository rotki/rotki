import { type AssetInfoWithId, bigNumberify } from '@rotki/common';
import { HYPERLIQUID_TOKEN_ADDRESS } from '@test/utils/asset-test-data';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  EVM_TOKEN,
  HYPERLIQUID_CORE_CHAIN,
  HYPERLIQUID_TOKEN,
  SOLANA_CHAIN,
  SOLANA_TOKEN,
} from '@/modules/assets/types';
import {
  assetDisplayCaption,
  assetDisplayLabel,
  assetFilterByKeyword,
  assetSuggestions,
  compareTextByKeyword,
  getAssetSearchTypeParams,
  getSanitizedChain,
  getSortItems,
  parseAssetSearchKeyword,
} from './assets';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): { getEvmChainName: (chain: string) => string | undefined; matchChain: (chain: string) => string | undefined } => ({
    getEvmChainName: (chain: string): string | undefined => (chain === 'eth' ? 'ethereum' : undefined),
    matchChain: (chain: string): string | undefined => (chain === 'ethereum' ? 'eth' : undefined),
  }),
}));

// `assetSuggestions` drops ignored assets, which is a store read. Hoisted so the set can be
// written per test without the mock factory closing over an uninitialised binding.
const { ignoredAssets } = vi.hoisted(() => ({ ignoredAssets: new Set<string>() }));

vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: (): { isAssetIgnored: (identifier: string) => boolean } => ({
    isAssetIgnored: (identifier: string): boolean => ignoredAssets.has(identifier),
  }),
}));

const DAI = '0x6B175474E89094C44Da98b954EedeAC495271d0F';

function info(symbol: string): AssetInfoWithId {
  return createMock<AssetInfoWithId>({ identifier: symbol, symbol });
}

describe('parseAssetSearchKeyword', () => {
  it('should treat a plain keyword as a value', () => {
    expect(parseAssetSearchKeyword('bitcoin')).toEqual({ value: 'bitcoin' });
  });

  it('should extract the address from an evm identifier', () => {
    expect(parseAssetSearchKeyword(`eip155:1/erc20:${DAI}`)).toEqual({ address: DAI, value: '' });
  });

  it('should treat a raw eth address as an address', () => {
    expect(parseAssetSearchKeyword(DAI)).toEqual({ address: DAI, value: '' });
  });

  it('should extract the address from a Hyperliquid Core identifier', () => {
    expect(parseAssetSearchKeyword(`hyperc:${HYPERLIQUID_TOKEN_ADDRESS}`)).toEqual({
      address: HYPERLIQUID_TOKEN_ADDRESS,
      value: '',
    });
  });

  it('should treat a raw Hyperliquid Core token ID as an address', () => {
    expect(parseAssetSearchKeyword(HYPERLIQUID_TOKEN_ADDRESS)).toEqual({
      address: HYPERLIQUID_TOKEN_ADDRESS,
      value: '',
    });
  });

  it('should normalize the address extracted from a Hyperliquid Core identifier', () => {
    const mixedCaseAddress = HYPERLIQUID_TOKEN_ADDRESS.toUpperCase().replace('0X', '0x');
    expect(parseAssetSearchKeyword(`hyperc:${mixedCaseAddress}`)).toEqual({
      address: HYPERLIQUID_TOKEN_ADDRESS,
      value: '',
    });
  });
});

describe('getSanitizedChain', () => {
  const matchChain = (chain: string): string | undefined => (chain === 'ethereum' ? 'eth' : undefined);
  const getEvmChainName = (chain: string): string | undefined => (chain === 'eth' ? 'ethereum' : undefined);

  it('should return undefined without a chain', () => {
    expect(getSanitizedChain(undefined, matchChain, getEvmChainName)).toBeUndefined();
  });

  it('should return undefined when the chain does not match', () => {
    expect(getSanitizedChain('unknown', matchChain, getEvmChainName)).toBeUndefined();
  });

  it('should return the evm chain name when resolvable', () => {
    expect(getSanitizedChain('ethereum', matchChain, getEvmChainName)).toBe('ethereum');
  });

  it('should preserve a supported non-EVM pseudo-chain without matching it as a blockchain', () => {
    expect(getSanitizedChain(HYPERLIQUID_CORE_CHAIN, matchChain, getEvmChainName)).toBe(HYPERLIQUID_CORE_CHAIN);
  });

  it('should fall back to the matched chain when no evm name exists', () => {
    const noEvmName = (): string | undefined => undefined;
    expect(getSanitizedChain('ethereum', matchChain, noEvmName)).toBe('eth');
  });
});

describe('getAssetSearchTypeParams', () => {
  it('should map the solana chain to the solana token type', () => {
    expect(getAssetSearchTypeParams(SOLANA_CHAIN)).toEqual({ assetType: SOLANA_TOKEN, evmChain: undefined });
  });

  it('should map Hyperliquid Core to the Hyperliquid token type', () => {
    expect(getAssetSearchTypeParams(HYPERLIQUID_CORE_CHAIN)).toEqual({
      assetType: HYPERLIQUID_TOKEN,
      evmChain: undefined,
    });
  });

  it('should map any other chain to the evm token type', () => {
    expect(getAssetSearchTypeParams('eth')).toEqual({ assetType: EVM_TOKEN, evmChain: 'eth' });
  });

  it('should leave both undefined without a chain', () => {
    expect(getAssetSearchTypeParams(undefined)).toEqual({ assetType: undefined, evmChain: undefined });
  });
});

describe('compareTextByKeyword', () => {
  it('should rank an exact match on the first string highest', () => {
    expect(compareTextByKeyword('hop', 'other', 'hop')).toBe(-1);
  });

  it('should rank an exact match on the second string highest', () => {
    expect(compareTextByKeyword('other', 'hop', 'hop')).toBe(1);
  });

  it('should prefer the string that starts with the keyword', () => {
    expect(compareTextByKeyword('hop-protocol', 'hoo', 'hop')).toBeLessThan(0);
  });
});

describe('getSortItems', () => {
  const sort = getSortItems<{ asset: string; amount: ReturnType<typeof bigNumberify>; value: ReturnType<typeof bigNumberify> }>(
    id => (id === 'a' ? info('AAA') : info('ZZZ')),
  );

  function item(asset: string, value: number): { asset: string; amount: ReturnType<typeof bigNumberify>; value: ReturnType<typeof bigNumberify> } {
    return { amount: bigNumberify(value), asset, value: bigNumberify(value) };
  }

  it('should sort by asset symbol ascending', () => {
    const result = sort([item('b', 1), item('a', 2)], ['asset'], [false]);
    expect(result.map(r => r.asset)).toEqual(['a', 'b']);
  });

  it('should sort by asset symbol descending', () => {
    const result = sort([item('a', 1), item('b', 2)], ['asset'], [true]);
    expect(result.map(r => r.asset)).toEqual(['b', 'a']);
  });

  it('should sort numeric columns ascending and descending', () => {
    const asc = sort([item('a', 5), item('b', 1)], ['value'], [false]);
    expect(asc.map(r => r.value.toNumber())).toEqual([1, 5]);
    const desc = sort([item('a', 1), item('b', 5)], ['value'], [true]);
    expect(desc.map(r => r.value.toNumber())).toEqual([5, 1]);
  });
});

describe('assetFilterByKeyword', () => {
  const getInfo = (id: string | undefined): { name?: string | null; symbol?: string | null } | null =>
    (id === 'dai' ? { name: 'Dai Stablecoin', symbol: 'DAI' } : null);

  it('should keep everything when the search is empty', () => {
    expect(assetFilterByKeyword({ amount: bigNumberify(1), asset: 'dai', value: bigNumberify(1) }, '', getInfo)).toBe(true);
  });

  it('should keep everything when the item is null', () => {
    expect(assetFilterByKeyword(null, 'dai', getInfo)).toBe(true);
  });

  it('should match on symbol or name', () => {
    expect(assetFilterByKeyword({ amount: bigNumberify(1), asset: 'dai', value: bigNumberify(1) }, 'dai', getInfo)).toBe(true);
    expect(assetFilterByKeyword({ amount: bigNumberify(1), asset: 'dai', value: bigNumberify(1) }, 'stablecoin', getInfo)).toBe(true);
  });

  it('should reject a non-matching keyword', () => {
    expect(assetFilterByKeyword({ amount: bigNumberify(1), asset: 'dai', value: bigNumberify(1) }, 'bitcoin', getInfo)).toBe(false);
  });

  it('should match an unresolved asset on its identifier', () => {
    const asset = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F';
    const item = { amount: bigNumberify(1), asset, value: bigNumberify(1) };
    expect(assetFilterByKeyword(item, '0x6b175474', getInfo)).toBe(true);
  });

  it('should reject an unresolved asset whose identifier does not match', () => {
    const asset = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F';
    const item = { amount: bigNumberify(1), asset, value: bigNumberify(1) };
    expect(assetFilterByKeyword(item, 'bitcoin', getInfo)).toBe(false);
  });
});

describe('assetSuggestions', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    ignoredAssets.clear();
  });

  it('should search with the parsed keyword and chain params', async () => {
    const assetSearch = vi.fn().mockResolvedValue([{ identifier: 'DAI', symbol: 'DAI' }]);
    const suggest = assetSuggestions(assetSearch, 'ethereum');

    const promise = suggest(DAI);
    await vi.advanceTimersByTimeAsync(200);
    const result = await promise;

    expect(result).toEqual([{ identifier: 'DAI', symbol: 'DAI' }]);
    expect(assetSearch).toHaveBeenCalledTimes(1);
    const params = assetSearch.mock.calls[0][0];
    expect(params.address).toBe(DAI);
    expect(params.assetType).toBe(EVM_TOKEN);
    expect(params.evmChain).toBe('ethereum');
    expect(params.limit).toBe(10);
  });

  // Every asset input in the app hides ignored assets (`AssetSelect` defaults `showIgnored` to
  // false), and the pill bar's own asset editor goes through `useAssetSearch`, which filters them.
  // Without this the same field behaved two ways: a spam asset offered while typing in the bar
  // could not be found in the checklist the pill opens.
  it('should drop ignored assets from the suggestions', async () => {
    ignoredAssets.add('SPAM');
    const assetSearch = vi.fn().mockResolvedValue([
      { identifier: 'DAI', symbol: 'DAI' },
      { identifier: 'SPAM', symbol: 'SPAM' },
    ]);
    const suggest = assetSuggestions(assetSearch, 'ethereum');

    const promise = suggest('dai');
    await vi.advanceTimersByTimeAsync(200);

    expect(await promise).toEqual([{ identifier: 'DAI', symbol: 'DAI' }]);
  });

  it('should search Hyperliquid Core suggestions using the Hyperliquid token asset type', async () => {
    const assetSearch = vi.fn().mockResolvedValue([]);
    const suggest = assetSuggestions(assetSearch, HYPERLIQUID_CORE_CHAIN);

    const promise = suggest('MAX');
    await vi.advanceTimersByTimeAsync(200);
    await promise;

    expect(assetSearch).toHaveBeenCalledWith(expect.objectContaining({
      assetType: HYPERLIQUID_TOKEN,
      evmChain: undefined,
    }));
  });
});

describe('assetDisplayLabel', () => {
  const unknown = 'eip155:1/erc20:0x214AF1443f6bB9FFB2bDcF301c762Df28Dd7f818';

  it('should use the symbol when the asset has one', () => {
    expect(assetDisplayLabel(unknown, 'USDC')).toBe('USDC');
  });

  // A raw identifier swamps a pill or a suggestion row, so an asset with no metadata falls back
  // to the shortened contract address instead.
  it('should fall back to the shortened address when there is no symbol', () => {
    expect(assetDisplayLabel(unknown)).toBe('0x214A...f818');
    expect(assetDisplayLabel(unknown, '  ')).toBe('0x214A...f818');
  });

  it('should fall back to the shortened Hyperliquid Core token ID', () => {
    expect(assetDisplayLabel(`hyperc:${HYPERLIQUID_TOKEN_ADDRESS}`)).toBe('0x6781...64af');
  });

  it('should truncate a non-evm identifier that has no address to extract', () => {
    expect(assetDisplayLabel('SOME-VERY-LONG-CUSTOM-IDENTIFIER')).toBe('SOME...FIER');
  });
});

describe('assetDisplayCaption', () => {
  const unknown = 'eip155:1/erc20:0x214AF1443f6bB9FFB2bDcF301c762Df28Dd7f818';

  it('should use the name when it is a real name', () => {
    expect(assetDisplayCaption(unknown, 'USD Coin')).toBe('USD Coin');
  });

  // An asset with no metadata reports its identifier as its name; echoing it under the label
  // would just repeat the row.
  it('should drop a name that is only the identifier again', () => {
    expect(assetDisplayCaption(unknown, unknown)).toBeUndefined();
    expect(assetDisplayCaption(unknown)).toBeUndefined();
  });
});
