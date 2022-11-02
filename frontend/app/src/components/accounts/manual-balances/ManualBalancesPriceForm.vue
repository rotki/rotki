<template>
  <div>
    <v-row>
      <v-col class="col" md="6">
        <amount-input
          v-model="price"
          :disabled="fetchingPrice || !isCustomPrice || pending"
          :loading="fetchingPrice"
          outlined
          :label="tc('common.price')"
        />
      </v-col>

      <v-col class="col" md="6">
        <asset-select
          v-model="priceAsset"
          :disabled="fetchingPrice || !isCustomPrice || pending"
          :loading="fetchingPrice"
          outlined
          :label="tc('manual_balances_form.fields.price_asset')"
        />
      </v-col>
    </v-row>

    <v-row v-if="assetMethod === 0 && fetchedPrice" class="mt-n10 mb-0">
      <v-col cols="auto">
        <v-checkbox
          v-model="isCustomPrice"
          :value="isCustomPrice"
          :disabled="pending"
          :label="tc('manual_balances_form.fields.input_manual_price')"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { api } from '@/services/rotkehlchen-api';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';

const props = defineProps({
  pending: {
    required: true,
    type: Boolean
  },
  assetMethod: {
    required: false,
    type: Number as PropType<number | null>,
    default: 0
  }
});

const { assetMethod } = toRefs(props);

const price = ref<string>('');
const priceAsset = ref<string>('');
const fetchingPrice = ref<boolean>(false);
const fetchedPrice = ref<string>('');
const isCustomPrice = ref<boolean>(false);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const {
  fetchPrices,
  toSelectedCurrency,
  assetPrice,
  isAssetPriceInCurrentCurrency
} = useBalancePricesStore();

const searchAssetPrice = async (asset: string) => {
  if (!asset) {
    set(price, '');
    set(priceAsset, '');
    set(fetchedPrice, '');
    set(isCustomPrice, true);
    return;
  }

  const mainCurrency = get(currencySymbol);
  if (mainCurrency === asset) {
    set(price, '1');
    set(priceAsset, mainCurrency);
    set(fetchedPrice, '1');
    set(isCustomPrice, false);
    return;
  }

  set(fetchingPrice, true);
  await fetchPrices({
    ignoreCache: true,
    selectedAssets: [asset]
  });
  set(fetchingPrice, false);

  const priceInFiat = get(assetPrice(asset));

  if (priceInFiat && !priceInFiat.eq(0)) {
    const priceInCurrentRate = get(toSelectedCurrency(priceInFiat)).toFixed();
    const isCurrentCurrency = get(isAssetPriceInCurrentCurrency(asset));

    const usedPrice = isCurrentCurrency
      ? priceInFiat.toFixed()
      : priceInCurrentRate;
    set(price, usedPrice);
    set(priceAsset, mainCurrency);
    set(fetchedPrice, usedPrice);
    set(isCustomPrice, false);
  } else {
    set(isCustomPrice, true);
  }
};

const savePrice = async (asset: string) => {
  if (get(isCustomPrice) && get(price) && get(priceAsset)) {
    await api.assets.addLatestPrice({
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
  } else {
    set(price, get(fetchedPrice));
    set(priceAsset, get(currencySymbol));
  }
});

watch(assetMethod, assetMethod => {
  if (assetMethod === 1) {
    set(price, '');
    set(priceAsset, '');
    set(isCustomPrice, true);
  } else if (get(fetchedPrice)) {
    set(price, get(fetchedPrice));
    set(priceAsset, CURRENCY_USD);
    set(isCustomPrice, false);
  }
});

const { tc } = useI18n();

defineExpose({
  searchAssetPrice,
  savePrice
});
</script>
