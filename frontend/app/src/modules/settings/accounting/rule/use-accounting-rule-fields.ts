import type { ComputedRef } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { toAccountingRuleFields } from '@/modules/settings/accounting/rule/accounting-rule-fields';

/**
 * The pill-bar fields for the accounting rules table. Built inside a computed so the labels track
 * the locale: fields built once at setup keep the language they were created in until the component
 * remounts.
 */
export function useAccountingRuleFields(): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Protocol resolution is the same for every table filtering on one, so it comes from one place
  // rather than being restated here.
  const shared = useSharedFieldResolvers();
  // The same mappings the table names its rows with, so a pill and the rows it filters read alike.
  const {
    getHistoryEventSubTypeName,
    getHistoryEventTypeName,
    historyEventSubTypes,
    historyEventTypes,
  } = useHistoryEventMappings();
  const { counterparties } = useHistoryEventCounterpartyMappings();

  return computed<FieldDef[]>(() => toAccountingRuleFields(shared, t, {
    counterparties: (): string[] => get(counterparties),
    eventSubtypeName: getHistoryEventSubTypeName,
    eventSubtypes: (): string[] => get(historyEventSubTypes),
    eventTypeName: getHistoryEventTypeName,
    eventTypes: (): string[] => get(historyEventTypes),
  }));
}
