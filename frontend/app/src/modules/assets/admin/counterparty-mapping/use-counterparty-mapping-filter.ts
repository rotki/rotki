import type { MatchedKeyword } from '@/modules/core/table/filtering';

/** The wire keys the counterparty mapping table filters on, which the URL carries too. */
export const CounterpartyMappingFilterKeys = {
  COUNTERPARTY: 'counterparty',
  COUNTERPARTY_SYMBOL: 'counterpartySymbol',
} as const;

export type CounterpartyMappingFilterKey =
  typeof CounterpartyMappingFilterKeys[keyof typeof CounterpartyMappingFilterKeys];

export type Filters = MatchedKeyword<CounterpartyMappingFilterKey>;
