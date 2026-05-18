import type { EvmChainEntries } from '@/modules/core/api/types/chains';
import { getChainIdFromEvmIdentifier } from '@rotki/common';
import { type NewDetectedToken, NewDetectedTokenKind } from './types';

/**
 * Resolves the chain location string for a newly-detected token.
 *
 * Used as the `location` prop for `HashLink` so the address/transaction column
 * shows the chain icon and the explorer link. We derive the chain straight from
 * the EVM identifier instead of waiting for the asset-info cache to populate —
 * just-detected tokens are typically not yet cached at first render.
 *
 * Returns the evm chain name (e.g. `'monad'`, `'ethereum'`) for EVM tokens
 * whose chain id is known, `'solana'` for Solana tokens, or the raw token kind
 * as a last-resort fallback.
 */
export function getTokenChain(
  token: Pick<NewDetectedToken, 'tokenIdentifier' | 'tokenKind'>,
  allEvmChains: EvmChainEntries,
): string {
  if (token.tokenKind !== NewDetectedTokenKind.EVM)
    return token.tokenKind;

  const chainId = getChainIdFromEvmIdentifier(token.tokenIdentifier);
  if (chainId === undefined)
    return token.tokenKind;

  return allEvmChains.find(entry => entry.id === chainId)?.name ?? token.tokenKind;
}
