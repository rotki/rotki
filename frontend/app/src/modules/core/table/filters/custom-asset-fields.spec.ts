import { describe, expect, it } from 'vitest';
import { toCustomAssetFields } from '@/modules/core/table/filters/custom-asset-fields';
import { CustomAssetFilterKeys, CustomAssetFilterValueKeys, type Matcher } from '@/modules/core/table/filters/use-custom-assets-filter';

const t = (key: string): string => key;

const matchers: Matcher[] = [
  {
    description: 'filter by name',
    key: CustomAssetFilterKeys.NAME,
    keyValue: CustomAssetFilterValueKeys.NAME,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  },
  {
    description: 'filter by type',
    key: CustomAssetFilterKeys.CUSTOM_ASSET_TYPE,
    keyValue: CustomAssetFilterValueKeys.CUSTOM_ASSET_TYPE,
    string: true,
    suggestions: (): string[] => ['vehicle'],
    validate: (value: string): boolean => value === 'vehicle',
  },
];

describe('toCustomAssetFields', () => {
  it('should give both fields their short pill label', () => {
    expect(toCustomAssetFields(matchers, t).map(field => field.label)).toStrictEqual([
      'assets.filter_field_labels.name',
      'assets.filter_field_labels.type',
    ]);
  });

  it('should type the name and pick the type', () => {
    const [name, type] = toCustomAssetFields(matchers, t);
    expect(name.freeText).toBe(true);
    expect(type.freeText).toBeUndefined();
    expect(type.suggest?.()).toStrictEqual(['vehicle']);
  });

  it('should keep the wire keys the table already sends', () => {
    expect(toCustomAssetFields(matchers, t).map(field => field.key)).toStrictEqual(['name', 'custom_asset_type']);
  });
});
