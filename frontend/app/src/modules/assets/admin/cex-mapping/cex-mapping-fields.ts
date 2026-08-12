import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { CexMappingFilterKeys } from '@/modules/assets/admin/cex-mapping/use-cex-mapping-filter';
import { toNameField } from '@/modules/core/table/filters/shared/name-field';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * The pill-bar fields for the cex mapping table: the exchange a mapping is for, and the symbol that
 * exchange calls the asset.
 *
 * Both were `extraParams` before, which is what a table reaches for when a filter has no field to
 * live in. Neither needed to be: the backend takes them as ordinary filters
 * (`LocationAssetMappingsPostSchema`), so they ride the filter bag like every other string filter.
 *
 * The symbol is typed rather than picked, the way a name is: there is no list of every symbol every
 * exchange uses, and the backend matches what is given.
 */
export function toCexMappingFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  exchanges: () => string[],
): FieldDef[] {
  return [
    decorateSharedField(
      toMatchFieldDef({
        key: CexMappingFilterKeys.LOCATION,
        // The pill says what the column says.
        label: (): string => t('common.exchange'),
        multiple: false,
        suggest: exchanges,
        // Checked against the same list it offers: the backend reads an unknown location as the
        // common mappings rather than as nothing, so a typo would quietly show the wrong rows.
        validate: (value: string): boolean => exchanges().includes(value),
      }),
      SharedFieldKinds.LOCATION,
      resolvers,
    ),
    toNameField(
      CexMappingFilterKeys.LOCATION_SYMBOL,
      (): string => t('asset_management.cex_mapping.asset_symbol'),
    ),
  ];
}
