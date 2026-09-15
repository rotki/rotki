import type { MessageHandler } from '../interfaces';
import type { NoAvailableIndexersData } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

/**
 * Sent by the backend when etherscan refused the chain for the configured key, which happens on
 * the chains its free tier does not cover, and no other indexer could serve it either.
 */
const ETHERSCAN_PAID_KEY_REQUIRED = 'etherscan_paid_key_required';

/**
 * Raises the action center row for a chain no indexer could serve.
 *
 * @remarks
 * Creates no notification. Suppressed chains are filtered where the row is read rather than here,
 * so suppressing a chain later also takes down a row raised before.
 */
export function createNoAvailableIndexersHandler(): MessageHandler<NoAvailableIndexersData> {
  const { raise } = useRaisedConditionsStore();

  return createConditionalHandler<NoAvailableIndexersData>(({ chain, reason }) => {
    raise({ chain, kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired: reason === ETHERSCAN_PAID_KEY_REQUIRED });
    return null;
  });
}
