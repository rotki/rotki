import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import { type EthValidatorStatus, ethValidatorStatuses } from '@rotki/common';

/** The wire keys the validators table filters on, which the URL carries too. */
export const EthValidatorFilterKeys = {
  INDEX: 'index',
  PUBLIC_KEY: 'publicKey',
  STATUS: 'status',
} as const;

type EthValidatorFilterKey = typeof EthValidatorFilterKeys[keyof typeof EthValidatorFilterKeys];

export type Filters = MatchedKeywordWithBehaviour<EthValidatorFilterKey>;

/** Re-exported under the name the filters here already use; the list itself is the shared one. */
export const validStatuses = ethValidatorStatuses;

export function isValidStatus(status: string): status is EthValidatorStatus {
  return Array.prototype.includes.call(validStatuses, status);
}
