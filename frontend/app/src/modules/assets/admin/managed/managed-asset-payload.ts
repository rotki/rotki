import type { ManagedAssetPayload } from '@/modules/assets/api/use-asset-management-api';
import { EvmTokenKind, onlyIfTruthy, type SupportedAsset, type UnderlyingToken } from '@rotki/common';
import { omit } from 'es-toolkit';
import { EVM_TOKEN, HYPERLIQUID_TOKEN, SOLANA_TOKEN } from '@/modules/assets/types';

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

/**
 * The optional fields, as the api wants them rather than as the inputs hold them.
 *
 * The form binds every optional text field to an empty string so the input has something to write
 * into. The api reads an absent field as "leave it out" and a null chain or kind as "this asset has
 * none", so an empty string has to become one of those before it is sent. The two oracle
 * identifiers are the exception: there an empty string is what clears them.
 */
function emptyToAbsent(asset: SupportedAsset): Partial<ManagedAssetPayload> {
  return {
    coingecko: asset.coingecko ?? '',
    cryptocompare: asset.cryptocompare ?? '',
    evmChain: onlyIfTruthy(asset.evmChain) ?? null,
    forked: onlyIfTruthy(asset.forked),
    protocol: onlyIfTruthy(asset.protocol),
    swappedFor: onlyIfTruthy(asset.swappedFor),
    tokenKind: onlyIfTruthy(asset.tokenKind) ?? null,
  };
}

/**
 * Turns the asset the form holds into the payload the api takes.
 *
 * The form keeps optional text fields as empty strings so the inputs have something to bind to, and
 * the api wants them gone rather than empty, which is most of what happens here. `ended` and
 * `active` are read-only server state the form carries but never edits, and `customAssetType`
 * belongs to a different endpoint.
 *
 * Which of the token-specific fields survive depends on the asset type, so the branches below are
 * the same decision the form makes when it decides which inputs to show.
 */
export function buildManagedAssetPayload(
  asset: SupportedAsset,
  underlyingTokens: UnderlyingToken[],
): ManagedAssetPayload {
  const payload: ManagedAssetPayload = omit({
    ...asset,
    ...emptyToAbsent(asset),
    underlyingTokens: underlyingTokens.length > 0 ? underlyingTokens : undefined,
  }, ['ended', 'active', 'customAssetType']);

  if (payload.assetType !== EVM_TOKEN)
    return { ...prepareNonEvmAssetPayload(payload), isRebasing: false };

  // Only a rebasing fungible token has a meaning, and only a collectible has an id.
  if (payload.tokenKind === EvmTokenKind.ERC721)
    return { ...payload, isRebasing: false };

  return omit(payload, ['collectibleId']);
}
