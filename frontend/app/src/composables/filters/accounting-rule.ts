import { z } from 'zod';
import type { FilterSchema } from '@/composables/filter-paginate';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/types/filtering';

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

  const { historyEventTypes, historyEventSubTypes } = useHistoryEventMappings();
  const { counterparties } = useHistoryEventCounterpartyMappings();
  const { t } = useI18n();

  const matchers = computed<Matcher[]>(() => [{
    key: AccountingRuleFilterKeys.EVENT_TYPE,
    keyValue: AccountingRuleFilterValueKeys.EVENT_TYPE,
    description: t('accounting_settings.rule.filter.event_type'),
    multiple: true,
    string: true,
    suggestions: (): string[] => get(historyEventTypes),
    validate: (type: string): boolean => !!type,
  }, {
    key: AccountingRuleFilterKeys.EVENT_SUBTYPE,
    keyValue: AccountingRuleFilterValueKeys.EVENT_SUBTYPE,
    description: t('accounting_settings.rule.filter.event_subtype'),
    multiple: true,
    string: true,
    suggestions: (): string[] => get(historyEventSubTypes),
    validate: (type: string): boolean => !!type,
  }, {
    key: AccountingRuleFilterKeys.COUNTERPARTY,
    keyValue: AccountingRuleFilterValueKeys.COUNTERPARTY,
    description: t('accounting_settings.rule.filter.counterparty'),
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
    [AccountingRuleFilterValueKeys.EVENT_TYPE]: OptionalMultipleString,
    [AccountingRuleFilterValueKeys.EVENT_SUBTYPE]: OptionalMultipleString,
  });

  return {
    matchers,
    filters,
    RouteFilterSchema,
  };
}
