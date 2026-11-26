import type { SpamPredictionToken } from '@/modules/assets/api/use-asset-spam-prediction-api';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { useSpamAssessments } from '@/modules/assets/spam/use-spam-assessments';
import { type NewDetectedToken, NewDetectedTokenKind } from './types';
import { type NewlyDetectedTokenRow, useNewlyDetectedTokenRows } from './use-newly-detected-token-rows';

interface UseNewlyDetectedPageRowsReturn {
  rows: ComputedRef<NewlyDetectedTokenRow[]>;
  /** The state of the page's spam estimates; `unavailable` once the estimate request failed. */
  spamStatus: ReturnType<typeof useSpamAssessments>['status'];
}

/**
 * The rows of the displayed page, each with the spam estimate of its token.
 *
 * @remarks
 * Only EVM tokens are sent for an estimate; the other rows keep none.
 */
export function useNewlyDetectedPageRows(tokens: MaybeRefOrGetter<NewDetectedToken[]>): UseNewlyDetectedPageRowsReturn {
  const spamTokens = computed<SpamPredictionToken[]>(() => toValue(tokens)
    .filter(token => token.tokenKind === NewDetectedTokenKind.EVM)
    .map(token => ({ identifier: token.tokenIdentifier, txReference: token.seenTxReference })));

  const { assessments, status: spamStatus } = useSpamAssessments(spamTokens);

  const rows = useNewlyDetectedTokenRows(tokens, assessments);

  return {
    rows,
    spamStatus,
  };
}
