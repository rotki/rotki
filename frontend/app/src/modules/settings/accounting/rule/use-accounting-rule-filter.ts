import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';

/** The wire keys the accounting rules table filters on, which the URL carries too. */
export const AccountingRuleFilterKeys = {
  COUNTERPARTY: 'counterparties',
  EVENT_SUBTYPE: 'eventSubtypes',
  EVENT_TYPE: 'eventTypes',
} as const;

type AccountingRuleFilterKey = typeof AccountingRuleFilterKeys[keyof typeof AccountingRuleFilterKeys];

export type Filters = MatchedKeywordWithBehaviour<AccountingRuleFilterKey>;
