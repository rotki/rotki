import { describe, expect, it } from 'vitest';
import { toCustomAssetFields } from '@/modules/assets/admin/custom/custom-asset-fields';
import { routeSchemaFromFields } from '@/modules/core/table/route';

const t = (key: string): string => key;

const types = (): string[] => ['vehicle'];

describe('toCustomAssetFields', () => {
  it('should give both fields their short pill label', () => {
    expect(toCustomAssetFields(types, t).map(field => field.label)).toStrictEqual([
      'assets.filter_field_labels.name',
      'assets.filter_field_labels.type',
    ]);
  });

  it('should type the name and pick the type', () => {
    const [name, type] = toCustomAssetFields(types, t);
    expect(name.freeText).toBe(true);
    expect(type.freeText).toBeUndefined();
    expect(type.suggest?.()).toStrictEqual(['vehicle']);
  });

  // The types come from what the user created, so a type that does not exist is refused rather
  // than sent as a filter that matches nothing.
  it('should refuse a type the user has not created', () => {
    const [, type] = toCustomAssetFields(types, t);
    expect(type.validate?.('vehicle')).toBe(true);
    expect(type.validate?.('spaceship')).toBe(false);
  });

  it('should keep the wire keys the table already sends', () => {
    expect(toCustomAssetFields(types, t).map(field => field.key)).toStrictEqual(['name', 'custom_asset_type']);
  });

  // The url shape of the filter bag is derived from these fields, so the round-trip is asserted
  // here rather than against a second hand-written declaration.
  it('should keep name and type route values as optional strings', () => {
    const schema = routeSchemaFromFields(toCustomAssetFields(types, t));

    expect(schema.parse({ custom_asset_type: 'fiat', name: 'gold' })).toEqual({
      custom_asset_type: 'fiat',
      name: 'gold',
    });
    expect(schema.parse({})).toEqual({});
  });
});
