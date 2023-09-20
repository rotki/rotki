<script setup lang="ts">
import { type BigNumber } from '@rotki/common';

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

const { t } = useI18n();

defineExpose({
  savePrice
});
</script>

<template>
  <div>
    <VRow class="pb-8">
      <VCol class="col" md="6">
        <AmountInput
          v-model="price"
          :disabled="fetchingPrice || !isCustomPrice || pending"
          :loading="fetchingPrice"
          outlined
          hide-details
          :label="t('common.price')"
        />
      </VCol>

      <VCol class="col" md="6">
        <AssetSelect
          v-model="priceAsset"
          :disabled="fetchingPrice || !isCustomPrice || pending"
          :loading="fetchingPrice"
          outlined
          hide-details
          :label="t('manual_balances_form.fields.price_asset')"
        />
      </VCol>
    </VRow>

    <div
      v-if="fiatPriceHint"
      class="mt-n10 mb-8 text-body-2 font-bold green--text"
    >
      <span
        >{{
          t('common.price_in_symbol', {
            symbol: currencySymbol
          })
        }}:
      </span>
      <span>
        <AmountDisplay :value="fiatPriceHint" :fiat-currency="currencySymbol" />
      </span>
    </div>

    <VRow v-if="fetchedPrice" class="mt-n10 mb-0">
      <VCol cols="auto">
        <VCheckbox
          v-model="isCustomPrice"
          :disabled="pending"
          :label="t('manual_balances_form.fields.input_manual_price')"
        />
      </VCol>
    </VRow>
  </div>
</template>
