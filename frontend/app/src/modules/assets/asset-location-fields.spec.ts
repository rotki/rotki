import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import {
  type AssetLocationFieldOptions,
  assetLocationParams,
  toAssetLocationFields,
} from '@/modules/assets/asset-location-fields';
import { DisplayKinds, type FieldDef } from '@/modules/core/table/pill/core/types';

const t = (key: string): string => key;

const resolvers: SharedFieldResolvers = {
  formatDate: (value: string): string => value,
  parseDate: (): string | undefined => undefined,
  resolveAssetChain: (): string | undefined => undefined,
  resolveAssetSymbol: (value: string): string => value,
  resolveChainName: (value: string): string => value,
  resolveHex: (value: string): string => `short:${value}`,
  resolveLocationName: (value: string): string => `name:${value}`,
  resolveProtocolName: (value: string): string => value,
  resolveTokenName: (value: string): string => value,
};

const options: AssetLocationFieldOptions = {
  accounts: {
    resolveCaption: (): string | undefined => undefined,
    resolveKeywords: (address: string): string => `${address} alice.eth`,
    resolveLabel: (address: string): string => `label:${address}`,
    suggest: (): string[] => ['0xabc'],
  },
  locations: (): string[] => ['kraken', 'polygon_pos'],
  tags: () => [{ name: 'savings', swatch: { background: '#ffffff', foreground: '#000000' } }],
};

const fields = (): FieldDef[] => toAssetLocationFields(resolvers, t, options);

function fieldOf(key: string): FieldDef | undefined {
  return fields().find(field => field.key === key);
}

describe('toAssetLocationFields', () => {
  it('should offer the three filters the selectors above the table used to be', () => {
    expect(fields().map(field => field.key)).toStrictEqual(['location', 'account', 'tags']);
  });

  it('should bind every field to a param, since this table filters the breakdown it already holds', () => {
    for (const field of fields()) {
      expect(field.binding).toMatchObject({ kind: 'param' });
    }
  });

  it('should offer the locations this asset is held at, by their raw id', () => {
    const location = fieldOf('location');

    expect(location?.suggest?.()).toStrictEqual(['kraken', 'polygon_pos']);
    expect(location?.display).toBe(DisplayKinds.LOCATION);
    expect(location?.resolveLabel?.('polygon_pos')).toBe('name:polygon_pos');
  });

  it('should take one location and several of everything else, a balance being held at one', () => {
    expect(fieldOf('location')?.multiple).toBe(false);
    expect(fieldOf('account')?.multiple).toBe(true);
    expect(fieldOf('tags')?.multiple).toBe(true);
  });

  it('should offer the accounts holding this asset, drawn as accounts', () => {
    const account = fieldOf('account');

    expect(account?.display).toBe(DisplayKinds.ACCOUNT);
    expect(account?.suggest?.()).toStrictEqual(['0xabc']);
    expect(account?.resolveLabel?.('0xabc')).toBe('label:0xabc');
    expect(account?.resolveKeywords?.('0xabc')).toBe('0xabc alice.eth');
  });

  it('should draw a tag in the colours it is recognised by', () => {
    expect(fieldOf('tags')?.resolveSwatch?.('savings')).toStrictEqual({
      background: '#ffffff',
      foreground: '#000000',
    });
  });

  it('should offer no exclusion on any field', () => {
    for (const field of fields()) {
      expect(field.allowExclusion).toBe(false);
      expect(field.operators).not.toContain('is_not');
    }
  });
});

describe('assetLocationParams', () => {
  it('should draw a pill for each key that is set', () => {
    const addresses = ref<string[]>(['0xabc']);
    const location = ref<string>('kraken');
    const tags = ref<string[]>(['a']);

    expect(get(assetLocationParams(addresses, location, tags))).toStrictEqual({
      addresses: ['0xabc'],
      location: 'kraken',
      tags: ['a'],
    });
  });

  it('should draw no pill for a key at its default', () => {
    expect(get(assetLocationParams(ref<string[]>([]), ref<string>(''), ref<string[]>([]))))
      .toStrictEqual({});
  });

  it('should write the models back from the bar\'s bag', () => {
    const addresses = ref<string[]>([]);
    const location = ref<string>('');
    const tags = ref<string[]>([]);
    const pillParams = assetLocationParams(addresses, location, tags);

    set(pillParams, { addresses: ['0xabc', '0xdef'], location: 'kraken', tags: ['a'] });

    expect(get(addresses)).toStrictEqual(['0xabc', '0xdef']);
    expect(get(location)).toBe('kraken');
    expect(get(tags)).toStrictEqual(['a']);
  });

  it('should clear every model when the pills are removed', () => {
    const addresses = ref<string[]>(['0xabc']);
    const location = ref<string>('kraken');
    const tags = ref<string[]>(['a']);

    set(assetLocationParams(addresses, location, tags), {});

    expect(get(addresses)).toStrictEqual([]);
    expect(get(location)).toBe('');
    expect(get(tags)).toStrictEqual([]);
  });
});
