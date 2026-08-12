import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toCexMappingFields } from '@/modules/assets/admin/cex-mapping/cex-mapping-fields';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/** The pill-bar fields for the cex mapping table. */
export function useCexMappingFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  // Location resolution is the same for every table filtering on one, so it comes from one place
  // rather than being restated here.
  const shared = useSharedFieldResolvers();
  // The same list the exchange selector offered here.
  const { allExchanges } = storeToRefs(useLocationStore());

  return toCexMappingFields(shared, t, (): string[] => get(allExchanges));
}
