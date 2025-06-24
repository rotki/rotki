import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/types/filtering';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { arrayify } from '@/utils/array';
import { z } from 'zod/v4';

enum AccountingRuleFilterKeys {
  EVENT_TYPE = 'event_type',
  EVENT_SUBTYPE = 'event_subtype',
  COUNTERPARTY = 'counterparty',
}

enum AccountingRuleFilterValueKeys {
  EVENT_TYPE = 'eventTypes',
  EVENT_SUBTYPE = 'eventSubtypes',
  COUNTERPARTY = 'counterparties',
}

export type Matcher = SearchMatcher<AccountingRuleFilterKeys, AccountingRuleFilterValueKeys>;

export type Filters = MatchedKeywordWithBehaviour<AccountingRuleFilterValueKeys>;

export function useAccountingRuleFilter(): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { historyEventSubTypes, historyEventTypes } = useHistoryEventMappings();
  const { counterparties } = useHistoryEventCounterpartyMappings();
  const { t } = useI18n({ useScope: 'global' });

  const matchers = computed<Matcher[]>(() => [{
    description: t('accounting_settings.rule.filter.event_type'),
    key: AccountingRuleFilterKeys.EVENT_TYPE,
    keyValue: AccountingRuleFilterValueKeys.EVENT_TYPE,
    multiple: true,
    string: true,
    suggestions: (): string[] => get(historyEventTypes),
    validate: (type: string): boolean => !!type,
  }, {
    description: t('accounting_settings.rule.filter.event_subtype'),
    key: AccountingRuleFilterKeys.EVENT_SUBTYPE,
    keyValue: AccountingRuleFilterValueKeys.EVENT_SUBTYPE,
    multiple: true,
    string: true,
    suggestions: (): string[] => get(historyEventSubTypes),
    validate: (type: string): boolean => !!type,
  }, {
    description: t('accounting_settings.rule.filter.counterparty'),
    key: AccountingRuleFilterKeys.COUNTERPARTY,
    keyValue: AccountingRuleFilterValueKeys.COUNTERPARTY,
    multiple: true,
    string: true,
    suggestions: (): string[] => get(counterparties),
    validate: (protocol: string): boolean => !!protocol,
  }]);

  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(arrayify)
    .optional();

  const RouteFilterSchema = z.object({
    [AccountingRuleFilterValueKeys.COUNTERPARTY]: OptionalMultipleString,
    [AccountingRuleFilterValueKeys.EVENT_SUBTYPE]: OptionalMultipleString,
    [AccountingRuleFilterValueKeys.EVENT_TYPE]: OptionalMultipleString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
