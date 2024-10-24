<script setup lang="ts">
import { toMessages } from '@/utils/validation';
import { CURRENCY_USD } from '@/types/currencies';
import { TaskType } from '@/types/task-type';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { DateFormat } from '@/types/date-format';
import type { Validation } from '@vuelidate/core';
import type { BigNumber } from '@rotki/common';
import type { HistoricalPriceFormPayload } from '@/types/prices';
import type { NewHistoryEventPayload } from '@/types/history/events';
import type { ActionStatus } from '@/types/action';

const amount = defineModel<string>('amount', { required: true });

const value = defineModel<string>('value', { required: true });

const props = withDefaults(
  defineProps<{
    datetime: string;
    asset: string;
    disableAsset?: boolean;
    v$: Validation;
    hidePriceFields?: boolean;
  }>(),
  {
    disableAsset: false,
    hidePriceFields: false,
  },
);

const emit = defineEmits<{
  (e: 'update:asset', asset: string): void;
}>();

const { datetime, asset, disableAsset, hidePriceFields } = toRefs(props);

const assetModel = computed({
  get() {
    return get(asset);
  },
  set(asset: string) {
    if (get(disableAsset))
      return;

    emit('update:asset', asset);
  },
});

const { t } = useI18n();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const isCurrentCurrencyUsd = computed<boolean>(() => get(currencySymbol) === CURRENCY_USD);

const fiatValue = ref<string>('');
const assetToPrice = ref<string>('');
const assetToFiatPrice = ref<string>('');

const { isTaskRunning } = useTaskStore();

const fetching = isTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

const fiatValueFocused = ref<boolean>(false);

const fetchedAssetToUsdPrice = ref<string>('');
const fetchedAssetToFiatPrice = ref<string>('');

const { resetHistoricalPricesData } = useHistoricCachePriceStore();

const { getHistoricPrice } = useBalancePricesStore();
const { addHistoricalPrice } = useAssetPricesApi();

async function savePrice(payload: HistoricalPriceFormPayload) {
  await addHistoricalPrice(payload);
  resetHistoricalPricesData([payload]);
}

const numericAssetToPrice = bigNumberifyFromRef(assetToPrice);
const numericAssetToFiatPrice = bigNumberifyFromRef(assetToFiatPrice);
const numericFiatValue = bigNumberifyFromRef(fiatValue);

const numericAmount = bigNumberifyFromRef(amount);
const numericValue = bigNumberifyFromRef(value);

function onAssetToPriceChange(forceUpdate = false) {
  if (get(amount) && get(assetToPrice) && (!get(fiatValueFocused) || forceUpdate))
    set(value, get(numericAmount).multipliedBy(get(numericAssetToPrice)).toFixed());
}

function onAssetToFiatPriceChanged(forceUpdate = false) {
  if (get(amount) && get(assetToFiatPrice) && (!get(fiatValueFocused) || forceUpdate))
    set(fiatValue, get(numericAmount).multipliedBy(get(numericAssetToFiatPrice)).toFixed());
}

function onValueChange() {
  if (get(amount) && get(fiatValueFocused))
    set(assetToPrice, get(numericValue).div(get(numericAmount)).toFixed());
}

function onFiatValueChange() {
  if (get(amount) && get(fiatValueFocused))
    set(assetToFiatPrice, get(numericFiatValue).div(get(numericAmount)).toFixed());
}

async function fetchHistoricPrices() {
  const datetimeVal = get(datetime);
  const assetVal = get(asset);
  if (!datetimeVal || !assetVal)
    return;

  const timestamp = convertToTimestamp(get(datetime), DateFormat.DateMonthYearHourMinuteSecond);

  if (assetVal === CURRENCY_USD) {
    set(fetchedAssetToUsdPrice, '1');
  }
  else {
    const price: BigNumber = await getHistoricPrice({
      timestamp,
      fromAsset: assetVal,
      toAsset: CURRENCY_USD,
    });

    if (price.gt(0))
      set(fetchedAssetToUsdPrice, price.toFixed());
  }

  if (!get(isCurrentCurrencyUsd)) {
    const currentCurrency = get(currencySymbol);

    if (assetVal === currentCurrency) {
      set(fetchedAssetToFiatPrice, '1');
      return;
    }

    const price = await getHistoricPrice({
      timestamp,
      fromAsset: assetVal,
      toAsset: currentCurrency,
    });

    if (price.gt(0))
      set(fetchedAssetToFiatPrice, price.toFixed());
  }
}

watch(
  [datetime, asset, hidePriceFields],
  async ([datetime, asset, hidePriceFields], [oldDatetime, oldAsset, oldHidePriceFields]) => {
    if (datetime !== oldDatetime || asset !== oldAsset || (oldHidePriceFields && !hidePriceFields))
      await fetchHistoricPrices();
  },
);

watch(fetchedAssetToUsdPrice, (price) => {
  set(assetToPrice, price);
  onAssetToPriceChange(true);
});

watch(assetToPrice, () => {
  onAssetToPriceChange();
});

watch(value, () => {
  onValueChange();
});

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
  if (get(isCurrentCurrencyUsd)) {
    onAssetToPriceChange();
    onValueChange();
  }
  else {
    onAssetToFiatPriceChanged();
    onFiatValueChange();
  }
});

async function submitPrice(payload: NewHistoryEventPayload): Promise<ActionStatus<ValidationErrors | string>> {
  if (get(hidePriceFields))
    return { success: true };

  const assetVal = get(asset);
  const timestamp = convertToTimestamp(get(datetime), DateFormat.DateMonthYearHourMinuteSecond);

  try {
    if (get(isCurrentCurrencyUsd)) {
      if (get(assetToPrice) !== get(fetchedAssetToUsdPrice)) {
        await savePrice({
          fromAsset: assetVal,
          toAsset: CURRENCY_USD,
          timestamp,
          price: get(assetToPrice),
        });
      }
    }
    else if (get(assetToFiatPrice) !== get(fetchedAssetToFiatPrice)) {
      await savePrice({
        fromAsset: assetVal,
        toAsset: get(currencySymbol),
        timestamp,
        price: get(assetToFiatPrice),
      });
    }

    return { success: true };
  }
  catch (error: any) {
    let message: ValidationErrors | string = error.message;
    if (error instanceof ApiValidationError)
      message = error.getValidationErrors(payload);

    return { success: false, message };
  }
}

function reset() {
  set(fetchedAssetToUsdPrice, '');
  set(fetchedAssetToFiatPrice, '');
  set(assetToPrice, '');
  set(assetToFiatPrice, '');
  set(fiatValue, '');
  set(value, '');
}

defineExpose({
  submitPrice,
  reset,
});
</script>

<template>
  <div>
    <div
      v-if="v$"
      class="grid md:grid-cols-2 gap-4 mb-4"
    >
      <AssetSelect
        v-model="assetModel"
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
        v-if="isCurrentCurrencyUsd"
        v-model:primary-value="assetToPrice"
        v-model:secondary-value="value"
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
          primary: toMessages(v$.value),
          secondary: toMessages(v$.value),
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
    </template>
  </div>
</template>
