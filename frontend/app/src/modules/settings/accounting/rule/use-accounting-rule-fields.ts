import type { MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/settings/accounting/rule/use-accounting-rule-filter';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { subtypesForTypes } from '@/modules/history/events/mapping/event-type-subtypes';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { toAccountingRuleFields } from '@/modules/settings/accounting/rule/accounting-rule-fields';

/**
 * Builds the pill-bar fields for the accounting rules table.
 *
 * @remarks
 * Takes the filter bag read-only, because the subtype field narrows by the picked event types.
 * That is why the caller owns the bag rather than leaving it to `useServerTable`.
 */
export function useAccountingRuleFields(filters: MaybeRefOrGetter<Filters>): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  const {
    getHistoryEventSubTypeName,
    getHistoryEventTypeName,
    historyEventTypeGlobalMapping,
    historyEventTypes,
  } = useHistoryEventMappings();
  const { counterparties } = useHistoryEventCounterpartyMappings();

  /**
   * Declared twice over — as the option list the subtype field offers, and as what it `admits` — so
   * the narrowing and the pruning of an already-picked subtype cannot disagree.
   */
  const subtypesFor = (eventTypes: readonly string[]): string[] =>
    subtypesForTypes(get(historyEventTypeGlobalMapping), eventTypes);

  const selectedEventTypes = computed<string[]>(() => {
    const picked = toValue(filters)?.eventTypes;
    if (picked === undefined)
      return [];

    return (Array.isArray(picked) ? picked : [picked]).map(entry => entry.toString());
  });

  return toAccountingRuleFields(shared, t, {
    counterparties: (): string[] => get(counterparties),
    eventSubtypeName: getHistoryEventSubTypeName,
    eventSubtypes: (): string[] => subtypesFor(get(selectedEventTypes)),
    eventTypeName: getHistoryEventTypeName,
    eventTypes: (): string[] => get(historyEventTypes),
    subtypesFor,
  });
}
