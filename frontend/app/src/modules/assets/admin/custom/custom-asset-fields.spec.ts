import { describe, expect, it } from 'vitest';
import { toCustomAssetFields } from '@/modules/assets/admin/custom/custom-asset-fields';
import { resolveText } from '@/modules/core/table/pill/core/text';
import { routeSchemaFromFields } from '@/modules/core/table/route';

const t = (key: string): string => key;

const types = (): string[] => ['vehicle'];

describe('toCustomAssetFields', () => {
  it('should give both fields their short pill label', () => {
    expect(toCustomAssetFields(types, t).map(field => resolveText(field.label))).toStrictEqual([
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

  it('should refuse a type the user has not created, rather than send a filter that matches nothing', () => {
    const [, type] = toCustomAssetFields(types, t);
    expect(type.validate?.('vehicle')).toBe(true);
    expect(type.validate?.('spaceship')).toBe(false);
  });

  it('should keep the wire keys the table already sends', () => {
    expect(toCustomAssetFields(types, t).map(field => field.key)).toStrictEqual(['name', 'custom_asset_type']);
  });

  it('should keep name and type route values as optional strings', () => {
    const schema = routeSchemaFromFields(toCustomAssetFields(types, t));

    expect(schema.parse({ custom_asset_type: 'fiat', name: 'gold' })).toEqual({
      custom_asset_type: 'fiat',
      name: 'gold',
    });
    expect(schema.parse({})).toEqual({});
  });
});
