import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { SpamAssessment } from './spam/use-newly-detected-spam-assessments';
import type { SpamPrediction } from '@/modules/assets/api/use-asset-spam-prediction-api';
import { type BigNumber, getAddressFromEvmIdentifier, getAddressFromSolanaIdentifier } from '@rotki/common';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getTokenChain } from './get-token-chain';
import { type NewDetectedToken, NewDetectedTokenKind } from './types';

export interface NewlyDetectedTokenRow extends NewDetectedToken {
  address: string;
  chain: string;
  price?: BigNumber;
  spamPrediction?: SpamPrediction | null;
  spamUnavailable?: boolean;
}

const TOKEN_KIND_MAPPING = {
  [NewDetectedTokenKind.EVM]: {
    addressFormatter: getAddressFromEvmIdentifier,
  },
  [NewDetectedTokenKind.SOLANA]: {
    addressFormatter: getAddressFromSolanaIdentifier,
  },
} as const;

/**
 * Presents the current page's stored tokens and the spam assessments attached to them.
 *
 * @remarks
 * Presentation only: the stored token is never rewritten, and a missing assessment stays missing
 * rather than becoming a zero score. An unsupported token is represented by a `null` prediction,
 * while an unavailable one is flagged separately so the table can state the difference.
 */
export function useNewlyDetectedTokenRows(
  tokens: MaybeRefOrGetter<NewDetectedToken[]>,
  assessments: MaybeRefOrGetter<Record<string, SpamAssessment>>,
): ComputedRef<NewlyDetectedTokenRow[]> {
  const { allEvmChains } = useSupportedChains();
  const { getAssetPrice } = usePriceUtils();

  return computed<NewlyDetectedTokenRow[]>(() => {
    const evmChains = get(allEvmChains);
    const spam = toValue(assessments);

    return toValue(tokens).map((token) => {
      const assessment = spam[token.tokenIdentifier];
      let spamPrediction: SpamPrediction | null | undefined;
      if (assessment?.status === 'ready')
        spamPrediction = assessment.prediction;
      else if (assessment?.status === 'unsupported')
        spamPrediction = null;

      return {
        ...token,
        address: TOKEN_KIND_MAPPING[token.tokenKind].addressFormatter(token.tokenIdentifier),
        chain: getTokenChain(token, evmChains),
        price: getAssetPrice(token.tokenIdentifier),
        spamPrediction,
        spamUnavailable: assessment?.status === 'unavailable',
      };
    });
  });
}
