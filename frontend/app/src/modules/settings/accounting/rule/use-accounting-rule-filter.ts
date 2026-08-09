import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { FilterKeyArities, filterRouteSchema } from '@/modules/core/table/route';

/** The wire keys the accounting rules table filters on, which the URL carries too. */
export const AccountingRuleFilterKeys = {
  COUNTERPARTY: 'counterparties',
  EVENT_SUBTYPE: 'eventSubtypes',
  EVENT_TYPE: 'eventTypes',
} as const;

export type AccountingRuleFilterKey = typeof AccountingRuleFilterKeys[keyof typeof AccountingRuleFilterKeys];

export type Filters = MatchedKeywordWithBehaviour<AccountingRuleFilterKey>;

export function useAccountingRuleFilter(): FilterSchema<Filters> {
  const modelFilters = ref<Filters>({});

  return {
    filters: modelFilters,
    RouteFilterSchema: filterRouteSchema({
      [AccountingRuleFilterKeys.COUNTERPARTY]: FilterKeyArities.MANY,
      [AccountingRuleFilterKeys.EVENT_SUBTYPE]: FilterKeyArities.MANY,
      [AccountingRuleFilterKeys.EVENT_TYPE]: FilterKeyArities.MANY,
    }),
  };
}
