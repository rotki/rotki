import type { AssetsWithId } from '@/modules/assets/types';
import type { TagFieldOption } from '@/modules/core/table/filters/shared/tag-field';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { toManualBalanceFields } from '@/modules/accounts/manual-balances/manual-balance-fields';
import { DisplayKinds } from '@/modules/core/table/pill/core/types';
import { routeSchemaFromFields } from '@/modules/core/table/route';

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
  it('should parse optional route filter values', () => {
    const schema = routeSchemaFromFields(fields());

    expect(schema.parse({ asset: 'ETH', label: 'x', location: 'kraken' })).toEqual({
      asset: 'ETH',
      label: 'x',
      location: 'kraken',
    });
    expect(schema.parse({})).toEqual({});
  });

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

  it('should have the label written rather than picked, it being a name the user gave', () => {
    const [, label] = fields();

    expect(label.freeText).toBe(true);
    expect(label.suggest).toBeUndefined();
  });

  it('should offer no exclusion on any field, since the request has no form for one', () => {
    for (const field of fields()) {
      expect(field.allowExclusion).toBe(false);
      expect(field.operators).not.toContain('is_not');
    }
  });
});
