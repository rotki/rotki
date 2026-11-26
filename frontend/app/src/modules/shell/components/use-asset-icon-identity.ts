import { getAddressFromEvmIdentifier, getIdentifierFromSymbolMap, isEvmIdentifier } from '@rotki/common';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { useBlockie } from '@/modules/accounts/use-blockie';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { isBlockchain } from '@/modules/core/common/chains';
import { hasAssetMetadata } from '@/modules/core/common/display/assets';
import { displayAssetText } from '@/modules/shell/components/asset-icon-display';

type AssetInfo = ReturnType<ReturnType<typeof useAssetInfoRetrieval>['useAssetInfo']>;

interface UseAssetIconIdentityReturn {
  asset: AssetInfo;
  /**
   * Blockie for an asset with nothing to call itself by. Its `displayAsset` falls back to the raw
   * identifier, so the generated text mark reads `eip` for every unknown EVM asset alike. A blockie
   * of the contract address at least tells two unknowns apart. Contract addresses are not user
   * identities, so unlike an account blockie this one needs no scrambling.
   */
  blockie: ComputedRef<string | undefined>;
  /** The unicode symbol of a fiat currency, which is drawn in place of an icon. */
  currency: ComputedRef<string | undefined>;
  displayAsset: ComputedRef<string>;
  /**
   * Whether the asset has anything to call itself by.
   *
   * @remarks
   * An asset with no metadata is still handed a name and a symbol, of the form `EVM Token: 0x…`.
   * Both are non-empty, so a plain `name ?? symbol` check reports "named" for exactly the assets that
   * have no name. Asked once here rather than in every consumer.
   */
  hasAssetText: ComputedRef<boolean>;
  isCustomAsset: ComputedRef<boolean>;
  mappedIdentifier: ComputedRef<string>;
  name: ComputedRef<string | undefined>;
  symbol: ComputedRef<string | undefined>;
}

/**
 * Resolves an asset icon's identifier to what the icon calls the asset: its fiat symbol, its
 * metadata and display text, or a blockie when it has nothing to call itself by.
 */
export function useAssetIconIdentity(
  identifier: MaybeRefOrGetter<string>,
  resolutionOptions: MaybeRefOrGetter<AssetResolutionOptions>,
): UseAssetIconIdentityReturn {
  const { getBlockie } = useBlockie();
  const { currencies } = useCurrencies();
  const { useAssetInfo } = useAssetInfoRetrieval();

  const mappedIdentifier = computed<string>(() => {
    const id = getIdentifierFromSymbolMap(toValue(identifier));
    return isBlockchain(id) ? id.toUpperCase() : id;
  });

  const currency = computed<string | undefined>(() => {
    const id = get(mappedIdentifier);
    const fiatCurrencies = get(currencies).filter(({ crypto }) => !crypto);
    return fiatCurrencies.find(({ tickerSymbol }) => tickerSymbol === id)?.unicodeSymbol;
  });

  const asset = useAssetInfo(mappedIdentifier, resolutionOptions);

  const isCustomAsset = computed(() => get(asset)?.isCustomAsset ?? false);
  const symbol = computed(() => get(asset)?.symbol);
  const name = computed(() => get(asset)?.name);

  const displayAsset = computed<string>(() =>
    displayAssetText(get(currency), get(symbol), get(name), get(mappedIdentifier)),
  );

  const hasAssetText = computed<boolean>(() => {
    if (get(currency))
      return true;
    const id = toValue(identifier);
    return hasAssetMetadata(id, get(symbol)) || hasAssetMetadata(id, get(name));
  });

  const blockie = computed<string | undefined>(() => {
    const id = toValue(identifier);
    if (get(hasAssetText) || !isEvmIdentifier(id))
      return undefined;
    const address = getAddressFromEvmIdentifier(id);
    return address ? getBlockie(address) : undefined;
  });

  return {
    asset,
    blockie,
    currency,
    displayAsset,
    hasAssetText,
    isCustomAsset,
    mappedIdentifier,
    name,
    symbol,
  };
}
