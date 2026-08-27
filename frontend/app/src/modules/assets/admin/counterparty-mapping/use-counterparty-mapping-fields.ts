import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toCounterpartyMappingFields } from '@/modules/assets/admin/counterparty-mapping/counterparty-mapping-fields';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';

/** The pill-bar fields for the counterparty mapping table. */
export function useCounterpartyMappingFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  const { counterparties } = useHistoryEventCounterpartyMappings();
  const { allExchanges } = storeToRefs(useLocationStore());

  const options = computed<string[]>(() => {
    const exchanges = get(allExchanges);
    return get(counterparties).filter(counterparty => !exchanges.includes(counterparty));
  });

  return toCounterpartyMappingFields(shared, t, (): string[] => get(options));
}
