import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { CustomAssetFilterKeys } from '@/modules/assets/admin/custom/use-custom-assets-filter';
import { toNameField } from '@/modules/core/table/filters/shared/name-field';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/** The pill-bar fields for the custom assets table: a written name and a picked type. */
export function toCustomAssetFields(types: () => string[], t: Translate): FieldDef[] {
  return [
    toNameField(CustomAssetFilterKeys.NAME, (): string => t('assets.filter_field_labels.name')),
    toMatchFieldDef({
      key: CustomAssetFilterKeys.CUSTOM_ASSET_TYPE,
      label: (): string => t('assets.filter_field_labels.type'),
      multiple: false,
      // The types the user has actually created, which is also what a typed value is checked
      // against so a type that does not exist is never applied.
      suggest: types,
      validate: (value: string): boolean => types().includes(value),
    }),
  ];
}
