import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';

/** The wire keys the validators table filters on, which the URL carries too. */
export const EthValidatorFilterKeys = {
  INDEX: 'index',
  PUBLIC_KEY: 'publicKey',
  STATUS: 'status',
} as const;

type EthValidatorFilterKey = typeof EthValidatorFilterKeys[keyof typeof EthValidatorFilterKeys];

export type Filters = MatchedKeywordWithBehaviour<EthValidatorFilterKey>;

export const validStatuses = ['exited', 'active', 'consolidated', 'all'] as const;

export function isValidStatus(status: string): status is (typeof validStatuses)[number] {
  return Array.prototype.includes.call(validStatuses, status);
}
