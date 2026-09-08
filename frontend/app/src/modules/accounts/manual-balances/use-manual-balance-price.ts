import type { BigNumber } from '@rotki/common';
import type { MaybeRefOrGetter, Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';

interface UseManualBalancePriceReturn {
  /** The price the form shows; the user types over it once the custom toggle is on. */
  modelPrice: Ref<string>;
  /** What the price is quoted in. */
  modelPriceAsset: Ref<string>;
  /** Whether the user is entering their own price rather than the one that was found. */
  modelIsCustomPrice: Ref<boolean>;
  /** Whether a price lookup is in flight. */
  fetchingPrice: Readonly<Ref<boolean>>;
  /** The price the lookup found, kept so the form can offer it back after a custom one. */
  fetchedPrice: Readonly<Ref<string>>;
  /** The fiat value shown beside a price quoted in something other than the main currency. */
  fiatPriceHint: Readonly<Ref<BigNumber | null>>;
  /** Looks the asset's price up and fills the form in with what it finds. */
  searchAssetPrice: () => Promise<void>;
  /** Saves the typed price as a custom one; does nothing unless the user entered one. */
  savePrice: (asset: string) => Promise<boolean>;
}

/**
 * The price a manual balance is valued at: what the app already knows, and what the user may
 * override it with.
 *
 * @remarks
 * The lookup prefers a custom price the user saved before, then the asset being the main currency
 * itself, then the oracle price. Anything else leaves the form blank, which turns the custom
 * toggle on so the user can supply one.
 *
 * @param asset - the asset the balance is in, re-read whenever it changes
 * @param currencySymbol - the user's main currency
 * @returns the price fields and the two actions over them
 */
export function useManualBalancePrice(
  asset: MaybeRefOrGetter<string>,
  currencySymbol: MaybeRefOrGetter<string>,
): UseManualBalancePriceReturn {
  const { addLatestPrice, fetchLatestPrices } = useAssetPricesApi();
  const { fetchPrices } = usePriceTaskManager();
  const { getAssetPrice } = usePriceUtils();

  const modelPrice = shallowRef<string>('');
  const modelPriceAsset = shallowRef<string>('');
  const modelIsCustomPrice = shallowRef<boolean>(false);
  const fetchedPrice = shallowRef<string>('');
  const fetchingPrice = shallowRef<boolean>(false);
  const fiatPriceHint = shallowRef<BigNumber | null>(null);

  async function oraclePrice(asset: string): Promise<BigNumber | null> {
    set(fetchingPrice, true);
    await fetchPrices({ ignoreCache: true, selectedAssets: [asset] });
    set(fetchingPrice, false);

    const price = getAssetPrice(asset);
    return price && !price.eq(0) ? price : null;
  }

  /** A blank price leaves the custom toggle on, since the form has nothing else to offer. */
  function setPrice(price = '', priceAsset = ''): void {
    set(modelPrice, price);
    set(modelPriceAsset, priceAsset);
    set(fetchedPrice, price);
    set(modelIsCustomPrice, !price || !priceAsset);
    set(fiatPriceHint, null);
  }

  async function searchAssetPrice(): Promise<void> {
    const current = toValue(asset);
    if (!current) {
      setPrice();
      return;
    }

    const mainCurrency = toValue(currencySymbol);

    const [saved] = await fetchLatestPrices({ fromAsset: current });
    if (saved) {
      setPrice(saved.price.toFixed(), saved.toAsset);

      if (mainCurrency !== saved.toAsset)
        set(fiatPriceHint, await oraclePrice(current));

      return;
    }

    if (mainCurrency === current) {
      setPrice('1', mainCurrency);
      return;
    }

    const price = await oraclePrice(current);
    setPrice(price ? price.toFixed() : undefined, price ? mainCurrency : undefined);
  }

  async function savePrice(asset: string): Promise<boolean> {
    if (!get(modelIsCustomPrice) || !get(modelPrice) || !get(modelPriceAsset))
      return false;

    return addLatestPrice({
      fromAsset: asset,
      price: get(modelPrice),
      toAsset: get(modelPriceAsset),
    });
  }

  /** Turning the toggle on empties the fields to type into; turning it off looks the price up again. */
  watch(modelIsCustomPrice, (isCustom) => {
    if (!isCustom) {
      startPromise(searchAssetPrice());
      return;
    }

    set(modelPrice, '');
    set(modelPriceAsset, '');
    set(fiatPriceHint, null);
  });

  watchImmediate(() => toValue(asset), () => {
    startPromise(searchAssetPrice());
  });

  return {
    fetchedPrice: readonly(fetchedPrice),
    fetchingPrice: readonly(fetchingPrice),
    fiatPriceHint: shallowReadonly(fiatPriceHint),
    modelIsCustomPrice,
    modelPrice,
    modelPriceAsset,
    savePrice,
    searchAssetPrice,
  };
}
