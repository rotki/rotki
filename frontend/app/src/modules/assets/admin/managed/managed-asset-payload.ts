import type { ManagedAssetPayload } from '@/modules/assets/api/use-asset-management-api';
import { omit } from 'es-toolkit';
import { HYPERLIQUID_TOKEN, SOLANA_TOKEN } from '@/modules/assets/types';

/**
 * Shapes a non-EVM asset form payload for its backend schema.
 * Solana keeps its address, decimals, protocol, and token kind. Hyperliquid Core keeps a
 * canonical address and decimals but has no protocol or token kind. The remaining branch is a
 * custom asset, which has none of the token-specific fields.
 */
export function prepareNonEvmAssetPayload(payload: ManagedAssetPayload): ManagedAssetPayload {
  const commonPayload = omit(payload, [
    'collectibleId',
    'underlyingTokens',
    'evmChain',
  ]);
  if (payload.assetType === SOLANA_TOKEN)
    return commonPayload;

  if (payload.assetType === HYPERLIQUID_TOKEN) {
    return {
      ...omit(commonPayload, ['protocol', 'tokenKind']),
      address: commonPayload.address?.toLowerCase() ?? commonPayload.address,
    };
  }

  return omit(commonPayload, ['decimals', 'address', 'tokenKind']);
}
