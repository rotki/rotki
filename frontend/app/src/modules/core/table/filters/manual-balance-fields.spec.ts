import type { TagFieldOption } from '@/modules/core/table/filters/shared/tag-field';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { toManualBalanceFields } from '@/modules/core/table/filters/manual-balance-fields';
import {
  ManualBalanceFilterKeys,
  ManualBalanceFilterValueKeys,
  type Matcher,
} from '@/modules/core/table/filters/use-manual-balances-filter';
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

const tags: TagFieldOption[] = [
  { name: 'savings', swatch: { background: '#ffffff', foreground: '#000000' } },
];

const matchers: Matcher[] = [
  {
    description: 'location',
    key: ManualBalanceFilterKeys.LOCATION,
    keyValue: ManualBalanceFilterValueKeys.LOCATION,
    string: true,
    suggestions: (): string[] => ['polygon_pos'],
    validate: (): boolean => true,
  },
  {
    description: 'label',
    key: ManualBalanceFilterKeys.LABEL,
    keyValue: ManualBalanceFilterValueKeys.LABEL,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  },
  {
    asset: true,
    description: 'asset',
    key: ManualBalanceFilterKeys.ASSET,
    keyValue: ManualBalanceFilterValueKeys.ASSET,
    suggestions: async (): Promise<string[]> => [],
  },
];

describe('toManualBalanceFields', () => {
  // The tags pill is the whole point of the migration here: it was a selector of its own beside
  // the bar, and it is param-bound rather than a matcher.
  it('should offer the tags beside the matchers', () => {
    expect(toManualBalanceFields(matchers, resolvers, t, () => tags).map(field => field.key)).toStrictEqual([
      'location',
      'label',
      'asset',
      'tags',
    ]);
  });

  it('should keep the tags pill on the param the table already sends', () => {
    const tagsField = toManualBalanceFields(matchers, resolvers, t, () => tags).at(-1);

    expect(tagsField).toMatchObject({ binding: { kind: 'param', paramKey: 'tags', to: 'both' } });
    expect(tagsField?.resolveSwatch?.('savings')).toStrictEqual({ background: '#ffffff', foreground: '#000000' });
  });

  it('should draw the location with its icon and display name', () => {
    const [location] = toManualBalanceFields(matchers, resolvers, t, () => tags);

    expect(location.display).toBe(DisplayKinds.LOCATION);
    expect(location.resolveLabel?.('polygon_pos')).toBe('Polygon PoS');
  });

  it('should draw the asset as an asset', () => {
    const asset = toManualBalanceFields(matchers, resolvers, t, () => tags).find(field => field.key === 'asset');

    expect(asset?.display).toBe(DisplayKinds.ASSET);
    expect(asset?.resolveLabel?.('eip155:1/erc20:0x6B17')).toBe('DAI');
  });

  // A label is the name the user gave the balance, so there is no list of them to offer.
  it('should have the label written rather than picked', () => {
    const [, label] = toManualBalanceFields(matchers, resolvers, t, () => tags);

    expect(label.freeText).toBe(true);
  });
});
