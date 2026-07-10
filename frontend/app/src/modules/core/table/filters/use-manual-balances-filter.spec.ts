import { assert, describe, expect, it, vi } from 'vitest';
import {
  ManualBalancesFilterSchema,
  useManualBalanceFilter,
} from '@/modules/core/table/filters/use-manual-balances-filter';

vi.mock('vue-i18n', async importOriginal => ({
  ...await importOriginal<typeof import('vue-i18n')>(),
  useI18n: (): { t: (key: string) => string } => ({ t: (key: string): string => key }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { assetSearch: () => Promise<never[]>; getAssetInfo: () => undefined } => ({
    assetSearch: async (): Promise<never[]> => [],
    getAssetInfo: (): undefined => undefined,
  }),
}));

vi.mock('@/modules/core/common/display/assets', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/common/display/assets')>(),
  assetSuggestions: (): (() => Promise<never[]>) => async (): Promise<never[]> => [],
}));

describe('useManualBalanceFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useManualBalanceFilter([]);
    expect(get(filters)).toEqual({});
  });

  it('should expose matchers for location, label and asset', () => {
    const { matchers } = useManualBalanceFilter([]);
    const keys = get(matchers).map(matcher => matcher.key);
    expect(keys).toEqual(['location', 'label', 'asset']);
  });

  it('should surface the provided location suggestions', () => {
    const { matchers } = useManualBalanceFilter(['kraken', 'binance']);
    const locationMatcher = get(matchers).find(matcher => matcher.key === 'location');
    assert(locationMatcher && 'string' in locationMatcher);
    expect(locationMatcher.suggestions()).toEqual(['kraken', 'binance']);
  });

  it('should validate the location against the provided list', () => {
    const { matchers } = useManualBalanceFilter(['kraken']);
    const locationMatcher = get(matchers).find(matcher => matcher.key === 'location');
    assert(locationMatcher && 'string' in locationMatcher);
    expect(locationMatcher.validate('kraken')).toBe(true);
    expect(locationMatcher.validate('unknown')).toBe(false);
  });

  it('should validate the label as any non-empty string', () => {
    const { matchers } = useManualBalanceFilter([]);
    const labelMatcher = get(matchers).find(matcher => matcher.key === 'label');
    assert(labelMatcher && 'string' in labelMatcher);
    expect(labelMatcher.validate('savings')).toBe(true);
    expect(labelMatcher.validate('')).toBe(false);
  });

  it('should parse optional route filter values', () => {
    const { RouteFilterSchema } = useManualBalanceFilter([]);
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({ asset: 'ETH', label: 'x', location: 'kraken' })).toEqual({
      asset: 'ETH',
      label: 'x',
      location: 'kraken',
    });
    expect(RouteFilterSchema.parse({})).toEqual({});
  });
});

describe('manualBalancesFilterSchema', () => {
  it('should split a comma-separated tags string into an array', () => {
    expect(ManualBalancesFilterSchema.parse({ tags: 'a,b,c' })).toEqual({ tags: ['a', 'b', 'c'] });
  });

  it('should default missing tags to an empty array', () => {
    expect(ManualBalancesFilterSchema.parse({})).toEqual({ tags: [] });
  });
});
