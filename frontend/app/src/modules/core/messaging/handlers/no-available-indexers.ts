import type { MessageHandler } from '../interfaces';
import type { NoAvailableIndexersData } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { NoIndexersCause, RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

/** The backend's `reason` for each cause it can send; anything else reads as no reason. */
const CAUSE_BY_REASON = new Map<string, NoIndexersCause>([
  ['blockscout_or_paid_etherscan_key_required', NoIndexersCause.BLOCKSCOUT_OR_PAID_ETHERSCAN_KEY],
  ['etherscan_paid_key_required', NoIndexersCause.PAID_ETHERSCAN_KEY],
]);

/** Blockscout answered with transactions it had not finished indexing, which passes on its own. */
const BLOCKSCOUT_INCOMPLETE_RESPONSE = 'blockscout_incomplete_response';

/**
 * Raises the action center row for a chain no indexer could serve.
 *
 * @remarks
 * Creates no notification. Suppressed chains are filtered where the row is read rather than here,
 * so suppressing a chain later also takes down a row raised before. An incomplete Blockscout
 * response raises nothing: no action fixes it, and the failed sync already shows on the account's
 * dock row until the next sync replaces it.
 */
export function createNoAvailableIndexersHandler(): MessageHandler<NoAvailableIndexersData> {
  const { raise } = useRaisedConditionsStore();

  return createConditionalHandler<NoAvailableIndexersData>(({ chain, reason }) => {
    if (reason === BLOCKSCOUT_INCOMPLETE_RESPONSE)
      return null;

    const cause = (reason === undefined ? undefined : CAUSE_BY_REASON.get(reason)) ?? NoIndexersCause.UNAVAILABLE;
    raise({ cause, chain, kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS });
    return null;
  });
}
