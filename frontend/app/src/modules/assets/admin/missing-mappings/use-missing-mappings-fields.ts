import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { MissingMappingsFilterKeys } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-filter';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { toNameField } from '@/modules/core/table/filters/shared/name-field';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';

/**
 * The pill-bar fields for the missing mappings table.
 *
 * These were a param source before, which reads as a wire contract and is not one: the rows come
 * from the local database and `getData` turns these two keys into a predicate over them. Nothing
 * about them was ever sent anywhere.
 */
export function useMissingMappingsFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  // The same list the exchange selector offered here.
  const { allExchanges } = storeToRefs(useLocationStore());
  const exchanges = (): string[] => get(allExchanges);

  return [
    decorateSharedField(
      toMatchFieldDef({
        key: MissingMappingsFilterKeys.LOCATION,
        label: (): string => t('common.location'),
        multiple: false,
        suggest: exchanges,
        validate: (value: string): boolean => exchanges().includes(value),
      }),
      SharedFieldKinds.LOCATION,
      shared,
    ),
    // Typed rather than picked, and matched as a prefix by the predicate.
    toNameField(
      MissingMappingsFilterKeys.IDENTIFIER,
      (): string => t('asset_management.cex_mapping.asset_symbol'),
    ),
  ];
}
