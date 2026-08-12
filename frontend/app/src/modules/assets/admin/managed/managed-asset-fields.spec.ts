import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { describe, expect, it } from 'vitest';
import {
  type ManagedAssetFieldOptions,
  toAssetIgnoredField,
  toAssetOwnedField,
  toAssetWhitelistedField,
  toManagedAssetFields,
} from '@/modules/assets/admin/managed/managed-asset-fields';
import { resolveText } from '@/modules/core/table/pill/core/text';
import { routeSchemaFromFields } from '@/modules/core/table/route';

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

const options: ManagedAssetFieldOptions = {
  assetTypes: (): string[] => ['evm token', 'solana token'],
  chains: (): string[] => ['ethereum', 'polygon_pos'],
};

const fields = (): FieldDef[] => toManagedAssetFields(resolvers, t, options);

function fieldOf(key: string): FieldDef | undefined {
  return fields().find(field => field.key === key);
}

describe('toManagedAssetFields', () => {
  it('should keep the wire keys the table already sends', () => {
    expect(fields().map(field => field.key)).toStrictEqual([
      'identifiers',
      'assetType',
      'assetFlag',
      'symbol',
      'name',
      'evmChain',
      'address',
    ]);
  });

  it('should give every field its short pill label', () => {
    expect(fields().map(field => resolveText(field.label))).toStrictEqual([
      'assets.filter_field_labels.identifier',
      'assets.filter_field_labels.asset_type',
      'assets.filter_field_labels.asset_flag',
      'assets.filter_field_labels.symbol',
      'assets.filter_field_labels.name',
      'assets.filter_field_labels.chain',
      'assets.filter_field_labels.address',
    ]);
  });

  it('should make the fields with no option list free text', () => {
    const freeText = fields().filter(field => field.freeText).map(field => field.key);

    expect(freeText).toStrictEqual(['identifiers', 'symbol', 'name', 'address']);
  });

  it('should offer the asset types and chains its table knows', () => {
    expect(fieldOf('assetType')?.suggest?.()).toStrictEqual(['evm token', 'solana token']);
    expect(fieldOf('evmChain')?.suggest?.()).toStrictEqual(['ethereum', 'polygon_pos']);
  });

  it('should apply only a flag the app defines', () => {
    const flag = fieldOf('assetFlag');

    expect(flag?.suggest?.()).toStrictEqual(['rebasing']);
    expect(flag?.validate?.('rebasing')).toBe(true);
    expect(flag?.validate?.('made_up')).toBe(false);
  });

  it('should draw a chain with its logo and display name', () => {
    const chain = fieldOf('evmChain');

    expect(chain?.display).toBe('chain');
    expect(chain?.resolveLabel?.('polygon_pos')).toBe('chain:polygon_pos');
  });

  it('should shorten a contract address rather than show it whole', () => {
    expect(fieldOf('address')?.resolveLabel?.('0x6B175474E89094C44Da98b954EedeAC495271d0F')).toBe('0x6B17...1d0F');
  });

  it('should rule the asset type and the chain out of each other', () => {
    expect(fieldOf('assetType')?.excludes).toStrictEqual(['evmChain']);
    expect(fieldOf('evmChain')?.excludes).toStrictEqual(['assetType']);
  });

  // `AssetsPostSchema` takes one of each of these; only `identifiers` is a list
  // (`DelimitedOrNormalList`, matched with `IN (...)`), which is also what the url has always
  // carried for it.
  it('should let only the identifiers field take more than one value', () => {
    expect(fields().filter(field => field.multiple).map(field => field.key)).toStrictEqual(['identifiers']);
  });

  // The url shape of the filter bag is derived from these fields, so the round-trip is asserted
  // here rather than against a second hand-written declaration.
  it('should read identifiers as a list and everything else as one value', () => {
    const schema = routeSchemaFromFields(fields());

    expect(schema.parse({ identifiers: 'eip155:1/erc20:0xdai', name: 'dai' }))
      .toEqual({ identifiers: ['eip155:1/erc20:0xdai'], name: 'dai' });
    expect(schema.parse({ identifiers: ['a', 'b'] })).toEqual({ identifiers: ['a', 'b'] });
    expect(schema.parse({})).toEqual({});
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
