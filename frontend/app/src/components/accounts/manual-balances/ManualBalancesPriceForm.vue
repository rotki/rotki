<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { FiatDisplay } from '@/modules/amount-display/components';
import { usePriceTaskManager } from '@/modules/prices/use-price-task-manager';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const { asset = '', pending } = defineProps<{
  pending: boolean;
  asset?: string;
}>();

const price = ref<string>('');
const priceAsset = ref<string>('');
const fetchingPrice = ref<boolean>(false);
const fetchedPrice = ref<string>('');
const isCustomPrice = ref<boolean>(false);
const fiatPriceHint = ref<BigNumber | null>();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { getAssetPrice } = usePriceUtils();
const { fetchPrices } = usePriceTaskManager();
const { addLatestPrice } = useAssetPricesApi();

const { fetchLatestPrices } = useAssetPricesApi();

async function getAssetPriceInFiat(asset: string): Promise<BigNumber | null> {
  set(fetchingPrice, true);
  await fetchPrices({
    ignoreCache: true,
    selectedAssets: [asset],
  });
  set(fetchingPrice, false);

  const priceInFiat = getAssetPrice(asset);

  if (priceInFiat && !priceInFiat.eq(0)) {
    return priceInFiat;
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
  if (!asset) {
    setPriceAndPriceAsset();
    return;
  }

  const mainCurrency = get(currencySymbol);

  const customLatestPrices = await fetchLatestPrices({ fromAsset: asset });
  if (customLatestPrices.length > 0) {
    const customLatestPrice = customLatestPrices[0];
    const newPrice = customLatestPrice.price.toFixed();
    const newPriceAsset = customLatestPrice.toAsset;

    setPriceAndPriceAsset(newPrice, newPriceAsset);

    if (mainCurrency !== newPriceAsset) {
      const priceInFiat = await getAssetPriceInFiat(asset);
      if (priceInFiat)
        set(fiatPriceHint, priceInFiat);
    }

    return;
  }

  if (mainCurrency === asset) {
    setPriceAndPriceAsset('1', mainCurrency);
    return;
  }

  const priceInFiat = await getAssetPriceInFiat(asset);
  if (priceInFiat) {
    setPriceAndPriceAsset(priceInFiat.toFixed(), mainCurrency);
    return;
  }

  setPriceAndPriceAsset();
}

async function savePrice(asset: string): Promise<boolean> {
  if (get(isCustomPrice) && get(price) && get(priceAsset)) {
    return await addLatestPrice({
      fromAsset: asset,
      price: get(price),
      toAsset: get(priceAsset),
    });
  }

  return false;
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

watchImmediate(() => asset, () => {
  searchAssetPrice();
});

const { t } = useI18n({ useScope: 'global' });

defineExpose({
  savePrice,
});
</script>

<template>
  <div>
    <div
      v-if="fetchedPrice"
      class="flex items-center gap-2 mb-8 justify-center"
    >
      <div
        class="text-sm"
        :class="{ 'text-rui-text-secondary': isCustomPrice }"
      >
        {{ t('manual_balances_form.fields.use_fetched_price') }}
      </div>
      <RuiSwitch
        v-model="isCustomPrice"
        hide-details
        color="primary"
        class="-my-2"
        :disabled="pending || fetchingPrice"
      />
      <div
        class="text-sm"
        :class="{ 'text-rui-text-secondary': !isCustomPrice }"
      >
        {{ t('manual_balances_form.fields.input_manual_price') }}
      </div>
    </div>
    <div class="grid grid-cols-2 gap-y-2">
      <AmountInput
        v-model="price"
        :disabled="fetchingPrice || !isCustomPrice || pending"
        :loading="fetchingPrice"
        variant="outlined"
        class="[&_fieldset]:!rounded-r-none"
        :label="t('common.price')"
      />
      <AssetSelect
        v-model="priceAsset"
        :disabled="fetchingPrice || !isCustomPrice || pending"
        :loading="fetchingPrice"
        outlined
        class="[&_fieldset]:!rounded-l-none"
        :hint="t('manual_balances_form.fields.price_asset_hint')"
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
      <FiatDisplay :value="fiatPriceHint" />
    </div>
  </div>
</template>
