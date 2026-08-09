import type { AssetsWithId } from '@/modules/assets/types';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { toOraclePriceFields } from '@/modules/assets/prices/oracle-price-fields';

const t = (key: string): string => key;

const resolvers: SharedFieldResolvers = {
  formatDate: (value: string): string => `date:${value}`,
  parseDate: (value: string): string | undefined => `ts:${value}`,
  resolveAssetChain: (value: string): string | undefined => `chainof:${value}`,
  resolveAssetSymbol: (value: string): string => `symbol:${value}`,
  resolveChainName: (value: string): string => `chain:${value}`,
  resolveHex: (value: string): string => `hex:${value}`,
  resolveLocationName: (value: string): string => `location:${value}`,
  resolveProtocolName: (value: string): string => `protocol:${value}`,
  resolveTokenName: (value: string): string => `token:${value}`,
};

const options = {
  resolveSourceLabel: (value: string): string => (value === 'coingecko' ? 'CoinGecko' : value),
  searchAsset: async (): Promise<AssetsWithId> => [],
  sources: (): string[] => ['coingecko', 'defillama'],
};

const fields = (): ReturnType<typeof toOraclePriceFields> => toOraclePriceFields(resolvers, t, options);

describe('toOraclePriceFields', () => {
  it('should declare the two assets, the source and one period field', () => {
    expect(fields().map(field => field.key)).toStrictEqual(['fromAsset', 'toAsset', 'sourceType', 'period']);
  });

  it('should fold the two date bounds into one period field', () => {
    const period = fields()[3];

    expect(period.valueType).toBe('date');
    expect(period.bounds).toStrictEqual({ lower: 'fromTimestamp', upper: 'toTimestamp' });
    expect(period.formatBound?.('1705320000')).toBe('date:1705320000');
    // No serializer of its own: a bound is stored as the timestamp it is sent as.
    expect(period.serializer).toBeUndefined();
  });

  it('should draw both assets with their icon, symbol and chain', () => {
    for (const asset of fields().slice(0, 2)) {
      expect(asset.display).toBe('asset');
      expect(asset.valueType).toBe('asset');
      expect(asset.resolveLabel?.('eip155:1/erc20:0xA0b8')).toBe('symbol:eip155:1/erc20:0xA0b8');
      expect(asset.resolveChain?.('eip155:1/erc20:0xA0b8')).toBe('chainof:eip155:1/erc20:0xA0b8');
    }
  });

  it('should pick an asset through the search rather than an option list', () => {
    const asset = fields()[0];

    expect(asset.searchAsset).toBeDefined();
    expect(asset.suggest).toBeUndefined();
    expect(asset.freeText).toBeUndefined();
  });

  it('should read a source the way the row it filters to does', () => {
    const source = fields()[2];

    expect(source.label).toBe('oracle_prices.filter_field_labels.source');
    expect(source.resolveLabel?.('coingecko')).toBe('CoinGecko');
    expect(source.suggest?.()).toStrictEqual(['coingecko', 'defillama']);
  });

  it('should apply only an oracle it offers', () => {
    const source = fields()[2];

    expect(source.validate?.('coingecko')).toBe(true);
    expect(source.validate?.('not-an-oracle')).toBe(false);
  });

  // None of these keys is declared as behaviour-carrying, so the request has no form for an
  // exclusion and the pill must not offer one.
  it('should offer no exclusion on any field', () => {
    for (const field of fields()) {
      expect(field.allowExclusion).toBe(false);
      expect(field.operators).not.toContain('is_not');
    }
  });
});
