<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';

const props = withDefaults(
  defineProps<{
    pending: boolean;
    asset?: string;
  }>(),
  {
    asset: '',
  },
);

const price = ref<string>('');
const priceAsset = ref<string>('');
const fetchingPrice = ref<boolean>(false);
const fetchedPrice = ref<string>('');
const isCustomPrice = ref<boolean>(false);
const fiatPriceHint = ref<BigNumber | null>();

const { asset } = toRefs(props);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetPrice, fetchPrices, isAssetPriceInCurrentCurrency, toSelectedCurrency } = useBalancePricesStore();
const { addLatestPrice } = useAssetPricesApi();

const { fetchLatestPrices } = useAssetPricesApi();

async function getAssetPriceInFiat(asset: string): Promise<BigNumber | null> {
  set(fetchingPrice, true);
  await fetchPrices({
    ignoreCache: true,
    selectedAssets: [asset],
  });
  set(fetchingPrice, false);

  const priceInFiat = get(assetPrice(asset));

  if (priceInFiat && !priceInFiat.eq(0)) {
    const priceInCurrentRate = get(toSelectedCurrency(priceInFiat));
    const isCurrentCurrency = get(isAssetPriceInCurrentCurrency(asset));

    return isCurrentCurrency ? priceInFiat : priceInCurrentRate;
  }

  return null;
}

function setPriceAndPriceAsset(newPrice = '', newPriceAsset = '') {
  set(price, newPrice);
  set(priceAsset, newPriceAsset);
  set(fetchedPrice, newPrice);
  set(isCustomPrice, !newPrice || !newPriceAsset);
  set(fiatPriceHint, null);
}

async function searchAssetPrice() {
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
      if (priceInFiat)
        set(fiatPriceHint, priceInFiat);
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
}

async function savePrice(asset: string) {
  if (get(isCustomPrice) && get(price) && get(priceAsset)) {
    await addLatestPrice({
      fromAsset: asset,
      price: get(price),
      toAsset: get(priceAsset),
    });
  }
}

watch(isCustomPrice, (isCustomPrice) => {
  if (isCustomPrice) {
    set(price, '');
    set(priceAsset, '');
    set(fiatPriceHint, null);
  }
  else {
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
  savePrice,
});
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <AmountInput
        v-model="price"
        :disabled="fetchingPrice || !isCustomPrice || pending"
        :loading="fetchingPrice"
        variant="outlined"
        :label="t('common.price')"
      />
      <AssetSelect
        v-model="priceAsset"
        :disabled="fetchingPrice || !isCustomPrice || pending"
        :loading="fetchingPrice"
        outlined
        :label="t('manual_balances_form.fields.price_asset')"
      />
    </div>

    <div
      v-if="fiatPriceHint"
      class="-mt-4 mb-4 text-body-2 font-bold text-rui-success"
    >
      {{
        t('common.price_in_symbol', {
          symbol: currencySymbol,
        })
      }}:
      <AmountDisplay
        :value="fiatPriceHint"
        :fiat-currency="currencySymbol"
      />
    </div>

    <RuiCheckbox
      v-if="fetchedPrice"
      v-model="isCustomPrice"
      color="primary"
      class="-my-2"
      :disabled="pending"
      :label="t('manual_balances_form.fields.input_manual_price')"
    />
  </div>
</template>
