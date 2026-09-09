import { type AssetInfoWithId, Blockchain } from '@rotki/common';
import { HYPERLIQUID_TOKEN, SOLANA_CHAIN, SOLANA_TOKEN } from '@/modules/assets/types';

/** What the tooltip's first line shows; an empty name collapses it to the symbol alone. */
export interface AssetTooltip {
  name: string;
  symbol: string;
}

/**
 * The chain badge to overlay on the icon.
 *
 * @remarks
 * An EVM asset carries its chain directly. Solana and Hyperliquid tokens do not, and are
 * recognised by their asset type instead. Anything else has no chain to show.
 *
 * @param forceChain - a chain the caller insists on, which wins over the asset's own
 * @param asset - the resolved asset, absent while it is still resolving
 * @returns the chain to badge, or undefined when there is none
 */
export function assetChain(
  forceChain: string | undefined,
  asset: AssetInfoWithId | null | undefined,
): string | undefined {
  if (forceChain)
    return forceChain;

  if (!asset)
    return undefined;

  if (asset.evmChain)
    return asset.evmChain;

  if (asset.assetType === SOLANA_TOKEN)
    return SOLANA_CHAIN;

  if (asset.assetType === HYPERLIQUID_TOKEN)
    return Blockchain.HYPERLIQUID;

  return undefined;
}

/**
 * The protocol badge, if the asset has one worth showing.
 *
 * @remarks
 * `spam` is a classification rather than a protocol, and badging it would give a spam token the
 * same treatment as a real one.
 *
 * @param protocol - the asset's protocol as resolved
 * @returns the protocol to badge, or undefined
 */
export function visibleProtocol(protocol: string | undefined): string | undefined {
  if (!protocol || protocol === 'spam')
    return undefined;

  return protocol;
}

/**
 * The text the icon falls back to when there is no image.
 *
 * @remarks
 * A fiat currency shows its unicode symbol, which is why the currency wins over the asset's own
 * names. The identifier is the last resort and is never empty, so the final `''` is unreachable
 * in practice and exists to keep the type a plain string.
 *
 * @returns whatever the icon can call the asset
 */
export function displayAssetText(
  currency: string | undefined,
  symbol: string | undefined,
  name: string | undefined,
  identifier: string | undefined,
): string {
  return currency ?? symbol ?? name ?? identifier ?? '';
}

/**
 * The two lines the tooltip shows for an asset.
 *
 * @remarks
 * The name is dropped when it would only repeat the symbol, which is the common case for a custom
 * asset (it has no symbol of its own, so its name is shown as one) and for assets whose symbol and
 * name match apart from case.
 *
 * @returns the name and symbol to render, either of which may be empty
 */
export function assetTooltip(
  name: string | undefined,
  symbol: string | undefined,
  isCustomAsset: boolean,
): AssetTooltip {
  const assetName = name ?? '';
  const assetSymbol = symbol ?? '';

  if (isCustomAsset)
    return { name: '', symbol: assetName };

  if (assetName.toLowerCase() === assetSymbol.toLowerCase())
    return { name: '', symbol: assetSymbol };

  return { name: assetName, symbol: assetSymbol };
}

/**
 * A badge size derived from the icon's own.
 *
 * @remarks
 * The caller's explicit size wins. Otherwise the badge is a percentage of the icon, so the two
 * scale together wherever the icon is used.
 *
 * @param override - a size the caller set, which wins outright
 * @param iconSize - the icon's size, as a css length whose leading number is used
 * @param percentage - how much of the icon the badge takes
 * @returns the badge size as a css length
 */
export function badgeSize(
  override: string | undefined,
  iconSize: string,
  percentage: number,
): string {
  if (override)
    return override;

  return `${(Number.parseInt(iconSize) * percentage) / 100}px`;
}
