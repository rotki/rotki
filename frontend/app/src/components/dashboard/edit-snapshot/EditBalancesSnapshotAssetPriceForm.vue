<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import useVuelidate from '@vuelidate/core';
import { toMessages } from '@/utils/validation';
import { CURRENCY_USD } from '@/types/currencies';
import { TaskType } from '@/types/task-type';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { useTaskStore } from '@/store/tasks';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import TwoFieldsAmountInput from '@/components/inputs/TwoFieldsAmountInput.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import type { HistoricalPriceFormPayload } from '@/types/prices';
import type { BigNumber } from '@rotki/common';

const amount = defineModel<string>('amount', { required: true });

const usdValue = defineModel<string>('usdValue', { required: true });

const asset = defineModel<string>('asset', { default: '', required: false });

const props = withDefaults(
  defineProps<{
    timestamp: number;
    disableAsset?: boolean;
    nft?: boolean;
  }>(),
  {
    disableAsset: false,
    nft: false,
  },
);

const { disableAsset, timestamp } = toRefs(props);

const { t } = useI18n();

const fiatValue = ref<string>('');
const assetToUsdPrice = ref<string>('');
const assetToFiatPrice = ref<string>('');

const fiatValueFocused = ref<boolean>(false);
const fetchedAssetToUsdPrice = ref<string>('');
const fetchedAssetToFiatPrice = ref<string>('');

const { resetHistoricalPricesData } = useHistoricCachePriceStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { isTaskRunning } = useTaskStore();

const { getHistoricPrice } = useBalancePricesStore();
const { addHistoricalPrice } = useAssetPricesApi();

const isCurrentCurrencyUsd = computed<boolean>(() => get(currencySymbol) === CURRENCY_USD);
const fetching = isTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

const numericAssetToUsdPrice = bigNumberifyFromRef(assetToUsdPrice);
const numericAssetToFiatPrice = bigNumberifyFromRef(assetToFiatPrice);
const numericFiatValue = bigNumberifyFromRef(fiatValue);

const numericAmount = bigNumberifyFromRef(amount);
const numericUsdValue = bigNumberifyFromRef(usdValue);

const rules = {
  amount: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.amount'), required),
  },
  asset: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.asset'), required),
  },
  usdValue: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.value'), required),
  },
};

const v$ = useVuelidate(
  rules,
  {
    amount,
    asset,
    usdValue,
  },
  {
    $autoDirty: true,
  },
);

async function savePrice(payload: HistoricalPriceFormPayload) {
  await addHistoricalPrice(payload);
  resetHistoricalPricesData([payload]);
}

function onAssetToUsdPriceChange(forceUpdate = false) {
  if (get(amount) && get(assetToUsdPrice) && (!get(fiatValueFocused) || forceUpdate))
    set(usdValue, get(numericAmount).multipliedBy(get(numericAssetToUsdPrice)).toFixed());
}

function onAssetToFiatPriceChanged(forceUpdate = false) {
  if (get(amount) && get(assetToFiatPrice) && (!get(fiatValueFocused) || forceUpdate))
    set(fiatValue, get(numericAmount).multipliedBy(get(numericAssetToFiatPrice)).toFixed());
}

function onUsdValueChange() {
  if (get(amount) && get(fiatValueFocused))
    set(assetToUsdPrice, get(numericUsdValue).div(get(numericAmount)).toFixed());
}

function onFiatValueChange() {
  if (get(amount) && get(fiatValueFocused))
    set(assetToFiatPrice, get(numericFiatValue).div(get(numericAmount)).toFixed());
}

async function fetchHistoricPrices() {
  const assetVal = get(asset);
  const timestampVal = get(timestamp);
  if (!timestampVal || !assetVal)
    return;

  const oldUsdPrice = get(numericUsdValue).dividedBy(get(numericAmount));

  if (assetVal === CURRENCY_USD) {
    set(fetchedAssetToUsdPrice, '1');
  }
  else {
    const price: BigNumber = await getHistoricPrice({
      fromAsset: assetVal,
      timestamp: timestampVal,
      toAsset: CURRENCY_USD,
    });

    if (price.gt(0)) {
      set(fetchedAssetToUsdPrice, price.toFixed());
    }
    else {
      set(assetToUsdPrice, oldUsdPrice.toFixed());
    }
  }

  if (!get(isCurrentCurrencyUsd)) {
    const currentCurrency = get(currencySymbol);

    if (assetVal === currentCurrency) {
      set(fetchedAssetToFiatPrice, '1');
      return;
    }

    const price = await getHistoricPrice({
      fromAsset: assetVal,
      timestamp: timestampVal,
      toAsset: currentCurrency,
    });

    if (price.gt(0)) {
      set(fetchedAssetToFiatPrice, price.toFixed());
    }
    else {
      set(assetToFiatPrice, oldUsdPrice.toFixed());
    }
  }
}

async function submitPrice(): Promise<void> {
  const assetVal = get(asset);
  const timestampVal = get(timestamp);

  if (!assetVal)
    return;

  if (get(isCurrentCurrencyUsd)) {
    if (get(assetToUsdPrice) !== get(fetchedAssetToUsdPrice)) {
      await savePrice({
        fromAsset: assetVal,
        price: get(assetToUsdPrice),
        timestamp: timestampVal,
        toAsset: CURRENCY_USD,
      });
    }
  }
  else if (get(assetToFiatPrice) !== get(fetchedAssetToFiatPrice)) {
    await savePrice({
      fromAsset: assetVal,
      price: get(assetToFiatPrice),
      timestamp: timestampVal,
      toAsset: get(currencySymbol),
    });
  }
}

function reset() {
  set(fetchedAssetToUsdPrice, '');
  set(fetchedAssetToFiatPrice, '');
  set(assetToUsdPrice, '');
  set(assetToFiatPrice, '');
  set(fiatValue, '');
  set(usdValue, '');
}

watchImmediate(
  [timestamp, asset],
  async ([timestamp, asset], [oldTimestamp, oldAsset]) => {
    if (timestamp !== oldTimestamp || asset !== oldAsset)
      await fetchHistoricPrices();
  },
);

watchImmediate(fetchedAssetToUsdPrice, (price) => {
  set(assetToUsdPrice, price);
  onAssetToUsdPriceChange(true);
});

watchImmediate(assetToUsdPrice, () => {
  onAssetToUsdPriceChange();
});

watchImmediate(usdValue, () => {
  onUsdValueChange();
});

watchImmediate(fetchedAssetToFiatPrice, (price) => {
  set(assetToFiatPrice, price);
  onAssetToFiatPriceChanged(true);
});

watchImmediate(assetToFiatPrice, () => {
  onAssetToFiatPriceChanged();
});

watchImmediate(fiatValue, () => {
  onFiatValueChange();
});

watchImmediate(amount, () => {
  if (!get(isCurrentCurrencyUsd)) {
    onAssetToFiatPriceChanged();
    onFiatValueChange();
  }

  onAssetToUsdPriceChange();
  onUsdValueChange();
});

defineExpose({
  reset,
  submitPrice,
});
</script>

<template>
  <div>
    <div
      v-if="v$"
      class="grid md:grid-cols-2 gap-4 mb-4"
    >
      <AssetSelect
        v-if="!nft"
        v-model="asset"
        outlined
        :disabled="disableAsset"
        show-ignored
        data-cy="asset"
        :error-messages="disableAsset ? [''] : toMessages(v$.asset)"
        @blur="v$.asset.$touch()"
      />
      <RuiTextField
        v-else
        v-model="asset"
        :label="t('common.asset')"
        variant="outlined"
        color="primary"
        :disabled="disableAsset"
        class="mb-1.5"
        :error-messages="disableAsset ? [''] : toMessages(v$.asset)"
        :hint="t('dashboard.snapshot.edit.dialog.balances.nft_hint')"
        @blur="v$.asset.$touch()"
      />
      <AmountInput
        v-model="amount"
        variant="outlined"
        data-cy="amount"
        :label="t('common.amount')"
        :error-messages="toMessages(v$.amount)"
        @blur="v$.amount.$touch()"
      />
    </div>
    <TwoFieldsAmountInput
      v-if="isCurrentCurrencyUsd"
      v-model:primary-value="assetToUsdPrice"
      v-model:secondary-value="usdValue"
      class="mb-5"
      :loading="fetching"
      :disabled="fetching"
      :label="{
        primary: t('transactions.events.form.asset_price.label', {
          symbol: currencySymbol,
        }),
        secondary: t('common.value_in_symbol', {
          symbol: currencySymbol,
        }),
      }"
      :error-messages="{
        primary: toMessages(v$.usdValue),
        secondary: toMessages(v$.usdValue),
      }"
      :hint="t('transactions.events.form.asset_price.hint')"
      @update:reversed="fiatValueFocused = $event"
    />

    <TwoFieldsAmountInput
      v-else
      v-model:primary-value="assetToFiatPrice"
      v-model:secondary-value="fiatValue"
      class="mb-5"
      :loading="fetching"
      :disabled="fetching"
      :label="{
        primary: t('transactions.events.form.asset_price.label', {
          symbol: currencySymbol,
        }),
        secondary: t('common.value_in_symbol', {
          symbol: currencySymbol,
        }),
      }"
      @update:reversed="fiatValueFocused = $event"
    />
  </div>
</template>
