import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import {
  toAssetIgnoredField,
  toAssetOwnedField,
  toAssetWhitelistedField,
  toManagedAssetFields,
} from '@/modules/core/table/filters/managed-asset-fields';
import { AssetFilterKeys, AssetFilterValueKeys, type Matcher } from '@/modules/core/table/filters/use-assets-filter';

const t = (key: string): string => key;

const resolvers: SharedFieldResolvers = {
  formatDate: (value: string): string => `date:${value}`,
  parseDate: (value: string): string | undefined => `ts:${value}`,
  resolveAssetChain: (): string | undefined => undefined,
  resolveAssetSymbol: (value: string): string => `symbol:${value}`,
  resolveChainName: (value: string): string => `chain:${value}`,
  resolveHex: (value: string): string => `hex:${value}`,
  resolveLocationName: (value: string): string => `location:${value}`,
  resolveProtocolName: (value: string): string => `protocol:${value}`,
  resolveTokenName: (value: string): string => `token:${value}`,
};

function matcher(key: AssetFilterKeys, keyValue: AssetFilterValueKeys): Matcher {
  return {
    description: `filter by ${key}`,
    key,
    keyValue,
    string: true,
    suggestions: (): string[] => [],
    validate: (): true => true,
  };
}

const matchers: Matcher[] = [
  matcher(AssetFilterKeys.IDENTIFIER, AssetFilterValueKeys.IDENTIFIER),
  matcher(AssetFilterKeys.ASSET_TYPE, AssetFilterValueKeys.ASSET_TYPE),
  matcher(AssetFilterKeys.SYMBOL, AssetFilterValueKeys.SYMBOL),
  matcher(AssetFilterKeys.CHAIN, AssetFilterValueKeys.CHAIN),
  matcher(AssetFilterKeys.ADDRESS, AssetFilterValueKeys.ADDRESS),
];

describe('toManagedAssetFields', () => {
  it('should give every field its short pill label', () => {
    const fields = toManagedAssetFields(matchers, resolvers, t);
    expect(fields.map(field => field.label)).toStrictEqual([
      'assets.filter_field_labels.identifier',
      'assets.filter_field_labels.asset_type',
      'assets.filter_field_labels.symbol',
      'assets.filter_field_labels.chain',
      'assets.filter_field_labels.address',
    ]);
  });

  it('should make the fields with no option list free text', () => {
    const fields = toManagedAssetFields(matchers, resolvers, t);
    const freeText = fields.filter(field => field.freeText).map(field => field.key);
    expect(freeText).toStrictEqual(['identifiers', 'symbol', 'address']);
  });

  it('should draw a chain with its logo and display name', () => {
    const chain = toManagedAssetFields(matchers, resolvers, t).find(field => field.key === 'evmChain');
    expect(chain?.display).toBe('chain');
    expect(chain?.resolveLabel?.('polygon_pos')).toBe('chain:polygon_pos');
  });

  it('should shorten a contract address rather than show it whole', () => {
    const address = toManagedAssetFields(matchers, resolvers, t).find(field => field.key === 'address');
    expect(address?.resolveLabel?.('0x6B175474E89094C44Da98b954EedeAC495271d0F')).toBe('0x6B17...1d0F');
  });

  it('should rule the asset type and the chain out of each other', () => {
    const fields = toManagedAssetFields(matchers, resolvers, t);
    expect(fields.find(field => field.key === 'assetType')?.excludes).toStrictEqual(['evmChain']);
    expect(fields.find(field => field.key === 'evmChain')?.excludes).toStrictEqual(['assetType']);
  });
});

describe('the status fields', () => {
  it('should bind owned and whitelisted as booleans on their own params', () => {
    expect(toAssetOwnedField(t)).toMatchObject({
      binding: { kind: 'param', paramKey: 'showUserOwnedAssetsOnly', to: 'both' },
      key: 'owned',
      valueType: 'boolean',
    });
    expect(toAssetWhitelistedField(t)).toMatchObject({
      binding: { kind: 'param', paramKey: 'showWhitelistedAssetsOnly', to: 'both' },
      key: 'whitelisted',
      valueType: 'boolean',
    });
  });

  it('should offer only the two departures from the default ignored handling', () => {
    const field = toAssetIgnoredField(t, value => `label:${value}`);
    expect(field.suggest?.()).toStrictEqual(['none', 'show_only']);
    expect(field.multiple).toBe(false);
    expect(field.binding).toStrictEqual({ kind: 'param', paramKey: 'ignoredAssetsHandling', to: 'both' });
  });

  it('should read an ignored value through the label its table resolves', () => {
    const field = toAssetIgnoredField(t, value => `label:${value}`);
    expect(field.resolveLabel?.('show_only')).toBe('label:show_only');
  });
});
