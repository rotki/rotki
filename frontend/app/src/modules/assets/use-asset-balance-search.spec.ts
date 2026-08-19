import { type AssetBalance, type AssetInfo, bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetBalanceSearch } from '@/modules/assets/use-asset-balance-search';

const DAI = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F';
const LINK = 'eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA';

const info: Record<string, AssetInfo> = {
  [DAI]: { name: 'Dai Stablecoin', symbol: 'DAI' },
  [LINK]: { name: 'ChainLink Token', symbol: 'LINK' },
  BTC: { name: 'Bitcoin', symbol: 'BTC' },
  LINKA: { name: 'Linka Token', symbol: 'LINKA' },
};

const resolvable = ref<Record<string, AssetInfo>>({});
const mockGetAssetInfo = vi.fn((identifier: string | undefined) =>
  (identifier ? get(resolvable)[identifier] ?? null : null));
const mockPrefetchAssetInfo = vi.fn<(identifiers: string[]) => void>();

vi.mock('@/modules/assets/use-asset-select-info', () => ({
  useAssetSelectInfo: (): { getAssetInfo: typeof mockGetAssetInfo; prefetchAssetInfo: typeof mockPrefetchAssetInfo } => ({
    getAssetInfo: mockGetAssetInfo,
    prefetchAssetInfo: mockPrefetchAssetInfo,
  }),
}));

function balance(asset: string, value = 1): AssetBalance {
  return { amount: bigNumberify(value), asset, value: bigNumberify(value) };
}

const ROWS = [balance(DAI, 300), balance(LINK, 200), balance('BTC', 100), balance('LINKA', 50)];

describe('useAssetBalanceSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(resolvable, info);
  });

  it('should return every balance when the search is empty', () => {
    const { matches } = useAssetBalanceSearch(ROWS, '');
    expect(get(matches)).toHaveLength(4);
  });

  it('should match on symbol', () => {
    const { matches } = useAssetBalanceSearch(ROWS, 'dai');
    expect(get(matches).map(r => r.asset)).toEqual([DAI]);
  });

  it('should match on name', () => {
    const { matches } = useAssetBalanceSearch(ROWS, 'stablecoin');
    expect(get(matches).map(r => r.asset)).toEqual([DAI]);
  });

  it('should match on the contract address', () => {
    const { matches } = useAssetBalanceSearch(ROWS, '0x514910');
    expect(get(matches).map(r => r.asset)).toEqual([LINK]);
  });

  it('should ignore case and punctuation in the search', () => {
    const { matches } = useAssetBalanceSearch(ROWS, '  ChainLink Token ');
    expect(get(matches).map(r => r.asset)).toEqual([LINK]);
  });

  it('should return nothing when no asset matches', () => {
    const { matches } = useAssetBalanceSearch(ROWS, 'monero');
    expect(get(matches)).toHaveLength(0);
  });

  it('should react to a change in the search term', () => {
    const search = ref('dai');
    const { matches } = useAssetBalanceSearch(ROWS, search);
    expect(get(matches).map(r => r.asset)).toEqual([DAI]);

    set(search, 'bitcoin');
    expect(get(matches).map(r => r.asset)).toEqual(['BTC']);
  });

  it('should react to a change in the balances', () => {
    const balances = ref<AssetBalance[]>([balance(DAI)]);
    const { matches } = useAssetBalanceSearch(balances, 'link');
    expect(get(matches)).toHaveLength(0);

    set(balances, [balance(DAI), balance(LINK)]);
    expect(get(matches).map(r => r.asset)).toEqual([LINK]);
  });

  it('should pick up metadata that resolves after the first search', () => {
    set(resolvable, {});
    const { matches } = useAssetBalanceSearch(ROWS, 'stablecoin');
    expect(get(matches)).toHaveLength(0);

    set(resolvable, info);
    expect(get(matches).map(r => r.asset)).toEqual([DAI]);
  });

  it('should match an unresolved asset on its identifier', () => {
    set(resolvable, {});
    const { matches } = useAssetBalanceSearch(ROWS, '0x514910');
    expect(get(matches).map(r => r.asset)).toEqual([LINK]);
  });

  it('should build the token index once per asset rather than per row read', () => {
    const search = ref('dai');
    const { matches } = useAssetBalanceSearch(ROWS, search);

    get(matches);
    get(matches);
    const afterFirstTerm = mockGetAssetInfo.mock.calls.length;
    expect(afterFirstTerm).toBe(ROWS.length);

    set(search, 'link');
    get(matches);
    expect(mockGetAssetInfo).toHaveBeenCalledTimes(afterFirstTerm);
  });

  it('should prefetch every balance so a search does not wait on the rendered page', () => {
    useAssetBalanceSearch(ROWS, '');
    expect(mockPrefetchAssetInfo).toHaveBeenCalledWith([DAI, LINK, 'BTC', 'LINKA']);
  });

  it('should prefetch again when the balances change', async () => {
    const balances = ref<AssetBalance[]>([balance(DAI)]);
    useAssetBalanceSearch(balances, '');
    expect(mockPrefetchAssetInfo).toHaveBeenLastCalledWith([DAI]);

    set(balances, [balance(DAI), balance(LINK)]);
    await nextTick();
    expect(mockPrefetchAssetInfo).toHaveBeenLastCalledWith([DAI, LINK]);
  });

  describe('prioritizeExactMatches', () => {
    it('should float an exact symbol match above better-ranked rows', () => {
      const { matches, prioritizeExactMatches } = useAssetBalanceSearch(ROWS, 'link');
      // The column sort put LINKA first; LINK is what was typed.
      const sorted = [...get(matches)].sort((a, b) => b.value.minus(a.value).toNumber());
      expect(sorted.map(r => r.asset)).toEqual([LINK, 'LINKA']);

      const prioritized = prioritizeExactMatches([balance('LINKA', 50), balance(LINK, 200)]);
      expect(prioritized.map(r => r.asset)).toEqual([LINK, 'LINKA']);
    });

    it('should float an exact name match', () => {
      const { prioritizeExactMatches } = useAssetBalanceSearch(ROWS, 'chainlink token');
      const prioritized = prioritizeExactMatches([balance('LINKA'), balance(LINK)]);
      expect(prioritized.map(r => r.asset)).toEqual([LINK, 'LINKA']);
    });

    it('should keep the given order among the rows it floats', () => {
      const rows = [balance(DAI), balance(LINK), balance('LINKA')];
      const { prioritizeExactMatches } = useAssetBalanceSearch(rows, 'link');
      expect(prioritizeExactMatches(rows).map(r => r.asset)).toEqual([LINK, DAI, 'LINKA']);
    });

    it('should leave the order untouched when nothing matches exactly', () => {
      const rows = [balance('LINKA'), balance(LINK)];
      const { prioritizeExactMatches } = useAssetBalanceSearch(rows, 'lin');
      expect(prioritizeExactMatches(rows)).toBe(rows);
    });

    it('should leave the order untouched when there is no search', () => {
      const rows = [balance('LINKA'), balance(LINK)];
      const { prioritizeExactMatches } = useAssetBalanceSearch(rows, '');
      expect(prioritizeExactMatches(rows)).toBe(rows);
    });
  });
});
