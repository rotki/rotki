<script setup lang="ts">
import type { ActionStatus } from '@/types/action';
import type { NewHistoryEventPayload } from '@/types/history/events';
import type { HistoricalPriceFormPayload } from '@/types/prices';
import type { Validation } from '@vuelidate/core';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import TwoFieldsAmountInput from '@/components/inputs/TwoFieldsAmountInput.vue';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { TaskType } from '@/types/task-type';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { toMessages } from '@/utils/validation';
import { assert, type BigNumber } from '@rotki/common';

interface HistoryEventAssetPriceFormProps {
  timestamp: number;
  disableAsset?: boolean;
  v$: Validation;
  hidePriceFields?: boolean;
}

const amount = defineModel<string>('amount', { required: true });
const asset = defineModel<string | undefined>('asset', { required: true });

const props = withDefaults(defineProps<HistoryEventAssetPriceFormProps>(), {
  disableAsset: false,
  hidePriceFields: false,
});

const { disableAsset, hidePriceFields, timestamp } = toRefs(props);

const { t } = useI18n();

const fiatValue = ref<string>('');
const assetToFiatPrice = ref<string>('');
const fiatValueFocused = ref<boolean>(false);
const fetchedAssetToFiatPrice = ref<string>('');

const { useIsTaskRunning } = useTaskStore();
const { resetHistoricalPricesData } = useHistoricCachePriceStore();
const { getHistoricPrice } = useBalancePricesStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { addHistoricalPrice } = useAssetPricesApi();

const fetching = useIsTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

const numericAssetToFiatPrice = bigNumberifyFromRef(assetToFiatPrice);
const numericFiatValue = bigNumberifyFromRef(fiatValue);
const numericAmount = bigNumberifyFromRef(amount);

async function savePrice(payload: HistoricalPriceFormPayload) {
  await addHistoricalPrice(payload);
  resetHistoricalPricesData([payload]);
}

function onAssetToFiatPriceChanged(forceUpdate = false) {
  if (get(amount) && get(assetToFiatPrice) && (!get(fiatValueFocused) || forceUpdate))
    set(fiatValue, get(numericAmount).multipliedBy(get(numericAssetToFiatPrice)).toFixed());
}

function onFiatValueChange() {
  if (get(amount) && get(fiatValueFocused))
    set(assetToFiatPrice, get(numericFiatValue).div(get(numericAmount)).toFixed());
}

async function fetchHistoricPrices() {
  const time = get(timestamp);
  const assetVal = get(asset);
  if (!time || !assetVal)
    return;

  const price: BigNumber = await getHistoricPrice({
    fromAsset: assetVal,
    timestamp: time,
    toAsset: get(currencySymbol),
  });

  if (price.gte(0))
    set(fetchedAssetToFiatPrice, price.toFixed());
}

watchImmediate(
  [timestamp, asset, hidePriceFields],
  async ([timestamp, asset, hidePriceFields], [oldTimestamp, oldAsset, oldHidePriceFields]) => {
    if (timestamp !== oldTimestamp || asset !== oldAsset || (oldHidePriceFields && !hidePriceFields))
      await fetchHistoricPrices();
  },
);

watch(fetchedAssetToFiatPrice, (price) => {
  set(assetToFiatPrice, price);
  onAssetToFiatPriceChanged(true);
});

watch(assetToFiatPrice, () => {
  onAssetToFiatPriceChanged();
});

watch(fiatValue, () => {
  onFiatValueChange();
});

watch(amount, () => {
  onAssetToFiatPriceChanged();
  onFiatValueChange();
});

async function submitPrice(payload: NewHistoryEventPayload): Promise<ActionStatus<ValidationErrors | string>> {
  if (get(hidePriceFields))
    return { success: true };

  const assetVal = get(asset);
  assert(assetVal);

  try {
    if (get(assetToFiatPrice) !== get(fetchedAssetToFiatPrice)) {
      await savePrice({
        fromAsset: assetVal,
        price: get(assetToFiatPrice),
        timestamp: get(timestamp),
        toAsset: get(currencySymbol),
      });
    }

    return { success: true };
  }
  catch (error: any) {
    let message: ValidationErrors | string = error.message;
    if (error instanceof ApiValidationError)
      message = error.getValidationErrors(payload);

    return { message, success: false };
  }
}

function reset() {
  set(fetchedAssetToFiatPrice, '');
  set(assetToFiatPrice, '');
  set(fiatValue, '');
}

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
        v-model="asset"
        outlined
        :disabled="disableAsset"
        data-cy="asset"
        :error-messages="disableAsset ? [''] : toMessages(v$.asset)"
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
    <template v-if="!hidePriceFields">
      <TwoFieldsAmountInput
        v-model:primary-value="assetToFiatPrice"
        v-model:secondary-value="fiatValue"
        class="mb-4"
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
    </template>
  </div>
</template>
