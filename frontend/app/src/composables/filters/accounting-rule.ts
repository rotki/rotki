import { z } from 'zod';
import {
  type MatchedKeywordWithBehaviour,
  type SearchMatcher
} from '@/types/filtering';

enum AccountingRuleFilterKeys {
  EVENT_TYPE = 'event_type',
  EVENT_SUBTYPE = 'event_subtype',
  COUNTERPARTY = 'counterparty'
}

enum AccountingRuleFilterValueKeys {
  EVENT_TYPE = 'eventTypes',
  EVENT_SUBTYPE = 'eventSubtypes',
  COUNTERPARTY = 'counterparties'
}

export type Matcher = SearchMatcher<
  AccountingRuleFilterKeys,
  AccountingRuleFilterValueKeys
>;

export type Filters =
  MatchedKeywordWithBehaviour<AccountingRuleFilterValueKeys>;

export const useAccountingRuleFilter = () => {
  const filters: Ref<Filters> = ref({});

  const { counterparties, historyEventTypes, historyEventSubTypes } =
    useHistoryEventMappings();
  const { t } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(() => [
    {
      key: AccountingRuleFilterKeys.EVENT_TYPE,
      keyValue: AccountingRuleFilterValueKeys.EVENT_TYPE,
      description: t('accounting_settings.rule.filter.event_type'),
      multiple: true,
      string: true,
      suggestions: () => get(historyEventTypes),
      validate: (type: string) => !!type
    },
    {
      key: AccountingRuleFilterKeys.EVENT_SUBTYPE,
      keyValue: AccountingRuleFilterValueKeys.EVENT_SUBTYPE,
      description: t('accounting_settings.rule.filter.event_subtype'),
      multiple: true,
      string: true,
      suggestions: () => get(historyEventSubTypes),
      validate: (type: string) => !!type
    },
    {
      key: AccountingRuleFilterKeys.COUNTERPARTY,
      keyValue: AccountingRuleFilterValueKeys.COUNTERPARTY,
      description: t('accounting_settings.rule.filter.counterparty'),
      multiple: true,
      string: true,
      suggestions: () => get(counterparties),
      validate: (protocol: string) => !!protocol
    }
  ]);

  const updateFilter = (newFilters: Filters) => {
    set(filters, newFilters);
  };

  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(val => (Array.isArray(val) ? val : [val]))
    .optional();

  const RouteFilterSchema = z.object({
    [AccountingRuleFilterValueKeys.COUNTERPARTY]: OptionalMultipleString,
    [AccountingRuleFilterValueKeys.EVENT_TYPE]: OptionalMultipleString,
    [AccountingRuleFilterValueKeys.EVENT_SUBTYPE]: OptionalMultipleString
  });

  return {
    matchers,
    filters,
    updateFilter,
    RouteFilterSchema
  };
};
