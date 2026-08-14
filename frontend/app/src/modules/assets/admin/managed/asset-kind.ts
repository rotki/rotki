import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { SelectOption } from '@/modules/core/common/common-types';
import { EvmTokenKind, toSentenceCase } from '@rotki/common';
import { CUSTOM_ASSET, EVM_TOKEN, HYPERLIQUID_TOKEN, SOLANA_TOKEN } from '@/modules/assets/types';

interface AssetKind {
  readonly isEvmToken: ComputedRef<boolean>;
  readonly isHyperliquidToken: ComputedRef<boolean>;
  readonly isSolanaToken: ComputedRef<boolean>;
  /** A collectible. It has an id instead of decimals, and cannot rebase. */
  readonly isNft: ComputedRef<boolean>;
  /** The three token types that are identified by an on-chain address. */
  readonly requiresAddress: ComputedRef<boolean>;
}

/**
 * Which fields an asset has, derived from its type and token kind.
 *
 * The form asks these five questions in a dozen places, to decide which inputs to render and which
 * rules apply, so they are answered once here rather than re-derived per binding.
 */
export function useAssetKind(
  assetType: MaybeRefOrGetter<string | null | undefined>,
  tokenKind: MaybeRefOrGetter<string | null | undefined>,
): AssetKind {
  const isEvmToken = computed<boolean>(() => toValue(assetType) === EVM_TOKEN);
  const isHyperliquidToken = computed<boolean>(() => toValue(assetType) === HYPERLIQUID_TOKEN);
  const isSolanaToken = computed<boolean>(() => toValue(assetType) === SOLANA_TOKEN);

  return {
    isEvmToken,
    isHyperliquidToken,
    isNft: computed<boolean>(() => toValue(tokenKind) === EvmTokenKind.ERC721),
    isSolanaToken,
    requiresAddress: computed<boolean>(
      () => get(isEvmToken) || get(isHyperliquidToken) || get(isSolanaToken),
    ),
  };
}

/**
 * The asset types this form offers.
 *
 * Custom assets are edited by their own form, so the type that would switch to it is not on the
 * list even when the backend reports it as supported.
 */
export function toAssetTypeOptions(assetTypes: string[]): SelectOption[] {
  return assetTypes
    .filter(type => type !== CUSTOM_ASSET)
    .map<SelectOption>(type => ({ key: type, label: toSentenceCase(type) }));
}
