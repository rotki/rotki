<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { useAssetPricesApi } from '@/services/assets/prices';

const props = withDefaults(
  defineProps<{
    pending: boolean;
    asset?: string;
  }>(),
  {
    asset: ''
  }
);

const price = ref<string>('');
const priceAsset = ref<string>('');
const fetchingPrice = ref<boolean>(false);
const fetchedPrice = ref<string>('');
const isCustomPrice = ref<boolean>(false);
const fiatPriceHint = ref<BigNumber | null>();

const { asset } = toRefs(props);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const {
  fetchPrices,
  toSelectedCurrency,
  assetPrice,
  isAssetPriceInCurrentCurrency
} = useBalancePricesStore();
const { addLatestPrice } = useAssetPricesApi();

const { fetchLatestPrices } = useAssetPricesApi();

const getAssetPriceInFiat = async (
  asset: string
): Promise<BigNumber | null> => {
  set(fetchingPrice, true);
  await fetchPrices({
    ignoreCache: true,
    selectedAssets: [asset]
  });
  set(fetchingPrice, false);

  const priceInFiat = get(assetPrice(asset));

  if (priceInFiat && !priceInFiat.eq(0)) {
    const priceInCurrentRate = get(toSelectedCurrency(priceInFiat));
    const isCurrentCurrency = get(isAssetPriceInCurrentCurrency(asset));

    return isCurrentCurrency ? priceInFiat : priceInCurrentRate;
  }

  return null;
};

const setPriceAndPriceAsset = (newPrice = '', newPriceAsset = '') => {
  set(price, newPrice);
  set(priceAsset, newPriceAsset);
  set(fetchedPrice, newPrice);
  set(isCustomPrice, !newPrice || !newPriceAsset);
  set(fiatPriceHint, null);
};

const searchAssetPrice = async () => {
  const assetProp = get(asset);

  if (!assetProp) {
    setPriceAndPriceAsset();
    return;
  }

  const mainCurrency = get(currencySymbol);

  const customLatestPrices = await fetchLatestPrices({ fromAsset: assetProp });
  if (customLatestPrices.length > 0) {
    const customLatestPrice = customLatestPrices[0];
    const newPrice = customLatestPrice.price.toFixed();
    const newPriceAsset = customLatestPrice.toAsset;

    setPriceAndPriceAsset(newPrice, newPriceAsset);

    if (mainCurrency !== newPriceAsset) {
      const priceInFiat = await getAssetPriceInFiat(assetProp);
      if (priceInFiat) {
        set(fiatPriceHint, priceInFiat);
      }
    }

    return;
  }

  if (mainCurrency === assetProp) {
    setPriceAndPriceAsset('1', mainCurrency);
    return;
  }

  const priceInFiat = await getAssetPriceInFiat(assetProp);
  if (priceInFiat) {
    setPriceAndPriceAsset(priceInFiat.toFixed(), mainCurrency);
    return;
  }

  setPriceAndPriceAsset();
};

const savePrice = async (asset: string) => {
  if (get(isCustomPrice) && get(price) && get(priceAsset)) {
    await addLatestPrice({
      fromAsset: asset,
      toAsset: get(priceAsset),
      price: get(price)
    });
  }
};

watch(isCustomPrice, isCustomPrice => {
  if (isCustomPrice) {
    set(price, '');
    set(priceAsset, '');
    set(fiatPriceHint, null);
  } else {
    searchAssetPrice();
  }
});

onMounted(() => {
  searchAssetPrice();
});

watch(asset, () => {
  searchAssetPrice();
});

const { tc } = useI18n();

defineExpose({
  savePrice
});
</script>

<template>
  <div>
    <v-row class="pb-8">
      <v-col class="col" md="6">
        <amount-input
          v-model="price"
          :disabled="fetchingPrice || !isCustomPrice || pending"
          :loading="fetchingPrice"
          outlined
          hide-details
          :label="tc('common.price')"
        />
      </v-col>

      <v-col class="col" md="6">
        <asset-select
          v-model="priceAsset"
          :disabled="fetchingPrice || !isCustomPrice || pending"
          :loading="fetchingPrice"
          outlined
          hide-details
          :label="tc('manual_balances_form.fields.price_asset')"
        />
      </v-col>
    </v-row>

    <div
      v-if="fiatPriceHint"
      class="mt-n10 mb-8 text-body-2 font-weight-bold green--text"
    >
      <span
        >{{
          tc('common.price_in_symbol', 0, {
            symbol: currencySymbol
          })
        }}:
      </span>
      <span>
        <amount-display
          :value="fiatPriceHint"
          :fiat-currency="currencySymbol"
        />
      </span>
    </div>

    <v-row v-if="fetchedPrice" class="mt-n10 mb-0">
      <v-col cols="auto">
        <v-checkbox
          v-model="isCustomPrice"
          :disabled="pending"
          :label="tc('manual_balances_form.fields.input_manual_price')"
        />
      </v-col>
    </v-row>
  </div>
</template>
