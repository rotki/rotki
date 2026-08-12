import { describe, expect, it, vi } from 'vitest';
import { useMissingMappingsFields } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-fields';
import { MissingMappingsFilterKeys } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-filter';
import { resolveText } from '@/modules/core/table/pill/core/text';
import { DisplayKinds } from '@/modules/core/table/pill/core/types';

vi.mock('@/modules/core/common/use-location-store', () => ({
  useLocationStore: (): Record<string, unknown> => ({
    allExchanges: ref(['kraken', 'binance']),
  }),
}));

vi.mock('@/modules/core/table/filters/shared/use-shared-field-resolvers', () => ({
  useSharedFieldResolvers: (): Record<string, unknown> => ({
    formatDate: (value: string): string => value,
    parseDate: (): undefined => undefined,
    resolveAssetChain: (): undefined => undefined,
    resolveAssetSymbol: (value: string): string => value,
    resolveChainName: (value: string): string => value,
    resolveHex: (value: string): string => value,
    resolveLocationName: (value: string): string => `Location(${value})`,
    resolveProtocolName: (value: string): string => value,
    resolveTokenName: (value: string): string => value,
  }),
}));

describe('useMissingMappingsFields', () => {
  // Not wire keys: these rows come from the local database and `getData` turns the two into a
  // predicate over them.
  it('should filter on the location and the symbol', () => {
    expect(useMissingMappingsFields().map(field => field.key)).toStrictEqual([
      MissingMappingsFilterKeys.LOCATION,
      MissingMappingsFilterKeys.IDENTIFIER,
    ]);
  });

  it('should give each field its short pill label', () => {
    expect(useMissingMappingsFields().map(field => resolveText(field.label))).toStrictEqual([
      'common.location',
      'asset_management.cex_mapping.asset_symbol',
    ]);
  });

  it('should draw the location as the shared location pill', () => {
    const [location] = useMissingMappingsFields();

    expect(location.display).toBe(DisplayKinds.LOCATION);
    expect(location.suggest?.()).toStrictEqual(['kraken', 'binance']);
    expect(location.resolveLabel?.('kraken')).toBe('Location(kraken)');
  });

  // The predicate compares the location exactly, so one that is not offered would match nothing and
  // read as an empty table rather than as a bad filter.
  it('should refuse a location it does not offer', () => {
    const [location] = useMissingMappingsFields();

    expect(location.validate?.('kraken')).toBe(true);
    expect(location.validate?.('nonsense')).toBe(false);
  });

  it('should type the symbol rather than pick it', () => {
    const [, identifier] = useMissingMappingsFields();

    expect(identifier.freeText).toBe(true);
    expect(identifier.suggest).toBeUndefined();
  });
});
