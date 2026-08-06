import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Matcher } from '@/modules/core/table/filters/use-accounting-rule-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toAccountingRuleFields } from '@/modules/core/table/filters/accounting-rule-fields';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

/**
 * The pill-bar fields for the accounting rules table. Built inside a computed so the labels track
 * the locale: fields built once at setup keep the language they were created in until the component
 * remounts.
 */
export function useAccountingRuleFields(matchers: MaybeRefOrGetter<Matcher[]>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Protocol resolution is the same for every table filtering on one, so it comes from one place
  // rather than being restated here.
  const shared = useSharedFieldResolvers();
  // The same mappings the table names its rows with, so a pill and the rows it filters read alike.
  const { getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();

  return computed<FieldDef[]>(() => toAccountingRuleFields(toValue(matchers), shared, t, {
    eventSubtypeName: getHistoryEventSubTypeName,
    eventTypeName: getHistoryEventTypeName,
  }));
}
