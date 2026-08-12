import { describe, expect, it } from 'vitest';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { toNameField } from '@/modules/core/table/filters/shared/name-field';

describe('toNameField', () => {
  it('should declare a written, single valued field on the table filter bag', () => {
    expect(toNameField('name', 'common.name')).toMatchObject({
      binding: { kind: 'filter' },
      freeText: true,
      key: 'name',
      label: 'common.name',
      multiple: false,
      valueType: FilterValueTypes.ENUM,
    });
  });

  it('should offer no option list, since there is no list of names to pick from', () => {
    const field = toNameField('label', 'common.label');

    expect(field.suggest).toBeUndefined();
    expect(field.validate).toBeUndefined();
  });
});
