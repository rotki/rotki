import type { AssetsWithId } from '@/modules/assets/types';
import type { TagFieldOption } from '@/modules/core/table/filters/shared/tag-field';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { toManualBalanceFields } from '@/modules/accounts/manual-balances/manual-balance-fields';
import { DisplayKinds } from '@/modules/core/table/pill/core/types';

const t = (key: string): string => key;

const resolvers: SharedFieldResolvers = {
  formatDate: (value: string): string => value,
  parseDate: (): string | undefined => undefined,
  resolveAssetChain: (): string | undefined => undefined,
  resolveAssetSymbol: (): string => 'DAI',
  resolveChainName: (value: string): string => value,
  resolveHex: (value: string): string => value,
  resolveLocationName: (): string => 'Polygon PoS',
  resolveProtocolName: (value: string): string => value,
  resolveTokenName: (value: string): string => value,
};

const options = {
  locations: (): string[] => ['polygon_pos', 'kraken'],
  searchAsset: async (): Promise<AssetsWithId> => [],
  tags: (): TagFieldOption[] => [
    { name: 'savings', swatch: { background: '#ffffff', foreground: '#000000' } },
  ],
};

const fields = (): ReturnType<typeof toManualBalanceFields> => toManualBalanceFields(resolvers, t, options);

describe('toManualBalanceFields', () => {
  // The tags pill is the whole point of the migration here: it was a selector of its own beside
  // the bar, and it is param-bound rather than part of the filter bag.
  it('should offer the tags beside the table own fields', () => {
    expect(fields().map(field => field.key)).toStrictEqual(['location', 'label', 'asset', 'tags']);
  });

  it('should keep the tags pill on the param the table already sends', () => {
    const tagsField = fields().at(-1);

    expect(tagsField).toMatchObject({ binding: { kind: 'param', paramKey: 'tags', to: 'both' } });
    expect(tagsField?.resolveSwatch?.('savings')).toStrictEqual({ background: '#ffffff', foreground: '#000000' });
  });

  it('should draw the location with its icon and display name', () => {
    const [location] = fields();

    expect(location.display).toBe(DisplayKinds.LOCATION);
    expect(location.resolveLabel?.('polygon_pos')).toBe('Polygon PoS');
    expect(location.suggest?.()).toStrictEqual(['polygon_pos', 'kraken']);
  });

  it('should apply only a location the user holds a balance in', () => {
    const [location] = fields();

    expect(location.validate?.('kraken')).toBe(true);
    expect(location.validate?.('nowhere')).toBe(false);
  });

  it('should draw the asset as an asset', () => {
    const asset = fields()[2];

    expect(asset.display).toBe(DisplayKinds.ASSET);
    expect(asset.valueType).toBe('asset');
    expect(asset.resolveLabel?.('eip155:1/erc20:0x6B17')).toBe('DAI');
    expect(asset.searchAsset).toBe(options.searchAsset);
  });

  // A label is the name the user gave the balance, so there is no list of them to offer.
  it('should have the label written rather than picked', () => {
    const [, label] = fields();

    expect(label.freeText).toBe(true);
    expect(label.suggest).toBeUndefined();
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
