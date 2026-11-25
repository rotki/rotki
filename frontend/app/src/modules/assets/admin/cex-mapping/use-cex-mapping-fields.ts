import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n';
import { toCexMappingFields } from '@/modules/assets/admin/cex-mapping/cex-mapping-fields';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/** The pill-bar fields for the cex mapping table. */
export function useCexMappingFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  // The same list the exchange selector offered here.
  const { allExchanges } = storeToRefs(useLocationStore());

  return toCexMappingFields(shared, t, (): string[] => get(allExchanges));
}
