import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { SpamAssessment } from '@/modules/assets/spam/use-spam-assessments';
import { type BigNumber, getAddressFromEvmIdentifier, getAddressFromSolanaIdentifier } from '@rotki/common';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getTokenChain } from './get-token-chain';
import { type NewDetectedToken, NewDetectedTokenKind } from './types';

export interface NewlyDetectedTokenRow extends NewDetectedToken {
  address: string;
  chain: string;
  price?: BigNumber;
  spamAssessment?: SpamAssessment;
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
 * rather than becoming a zero score.
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

    return toValue(tokens).map(token => ({
      ...token,
      address: TOKEN_KIND_MAPPING[token.tokenKind].addressFormatter(token.tokenIdentifier),
      chain: getTokenChain(token, evmChains),
      price: getAssetPrice(token.tokenIdentifier),
      spamAssessment: spam[token.tokenIdentifier],
    }));
  });
}
