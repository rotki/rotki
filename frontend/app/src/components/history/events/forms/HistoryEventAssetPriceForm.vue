<script setup lang="ts">
import { type Validation } from '@vuelidate/core';
import { type BigNumber } from '@rotki/common';
import { toMessages } from '@/utils/validation';
import { CURRENCY_USD } from '@/types/currencies';
import { TaskType } from '@/types/task-type';
import { type HistoricalPriceFormPayload } from '@/types/prices';
import { type NewHistoryEventPayload } from '@/types/history/events';
import { type ActionStatus } from '@/types/action';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { DateFormat } from '@/types/date-format';

const props = withDefaults(
  defineProps<{
    datetime: string;
    asset: string;
    amount: string;
    usdValue: string;
    disableAsset?: boolean;
    v$: Validation;
  }>(),
  {
    disableAsset: false
  }
);

const emit = defineEmits<{
  (e: 'update:asset', asset: string): void;
  (e: 'update:amount', amount: string): void;
  (e: 'update:usd-value', usdValue: string): void;
}>();

const { datetime, amount, usdValue, asset, disableAsset } = toRefs(props);

const assetModel = computed({
  get() {
    return get(asset);
  },
  set(asset: string) {
    if (get(disableAsset)) {
      return;
    }
    emit('update:asset', asset);
  }
});

const amountModel = computed({
  get() {
    return get(amount);
  },
  set(amount: string) {
    emit('update:amount', amount);
  }
});

const usdValueModel = computed({
  get() {
    return get(usdValue);
  },
  set(usdValue: string) {
    emit('update:usd-value', usdValue);
  }
});

const { t } = useI18n();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const isCurrentCurrencyUsd: ComputedRef<boolean> = computed(
  () => get(currencySymbol) === CURRENCY_USD
);

const fiatValue: Ref<string> = ref('');
const assetToUsdPrice: Ref<string> = ref('');
const assetToFiatPrice: Ref<string> = ref('');

const { isTaskRunning } = useTaskStore();

const fetching = isTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

const fiatValueFocused: Ref<boolean> = ref(false);

const fetchedAssetToUsdPrice: Ref<string> = ref('');
const fetchedAssetToFiatPrice: Ref<string> = ref('');

const { resetHistoricalPricesData } = useHistoricCachePriceStore();

const { getHistoricPrice } = useBalancePricesStore();
const { addHistoricalPrice } = useAssetPricesApi();

const savePrice = async (payload: HistoricalPriceFormPayload) => {
  await addHistoricalPrice(payload);
  resetHistoricalPricesData([payload]);
};

const numericAssetToUsdPrice = bigNumberifyFromRef(assetToUsdPrice);
const numericAssetToFiatPrice = bigNumberifyFromRef(assetToFiatPrice);
const numericFiatValue = bigNumberifyFromRef(fiatValue);

const numericAmount = bigNumberifyFromRef(amount);
const numericUsdValue = bigNumberifyFromRef(usdValue);

const onAssetToUsdPriceChange = (forceUpdate = false) => {
  if (
    get(amount) &&
    get(assetToUsdPrice) &&
    (!get(fiatValueFocused) || forceUpdate)
  ) {
    set(
      usdValueModel,
      get(numericAmount).multipliedBy(get(numericAssetToUsdPrice)).toFixed()
    );
  }
};

const onAssetToFiatPriceChanged = (forceUpdate = false) => {
  if (
    get(amount) &&
    get(assetToFiatPrice) &&
    (!get(fiatValueFocused) || forceUpdate)
  ) {
    set(
      fiatValue,
      get(numericAmount).multipliedBy(get(numericAssetToFiatPrice)).toFixed()
    );
  }
};

const onUsdValueChange = () => {
  if (get(amount) && get(fiatValueFocused)) {
    set(
      assetToUsdPrice,
      get(numericUsdValue).div(get(numericAmount)).toFixed()
    );
  }
};

const onFiatValueChange = () => {
  if (get(amount) && get(fiatValueFocused)) {
    set(
      assetToFiatPrice,
      get(numericFiatValue).div(get(numericAmount)).toFixed()
    );
  }
};

const fetchHistoricPrices = async () => {
  const datetimeVal = get(datetime);
  const assetVal = get(asset);
  if (!datetimeVal || !assetVal) {
    return;
  }

  const timestamp = convertToTimestamp(
    get(datetime),
    DateFormat.DateMonthYearHourMinuteSecond
  );

  let price: BigNumber = await getHistoricPrice({
    timestamp,
    fromAsset: assetVal,
    toAsset: CURRENCY_USD
  });

  if (price.gt(0)) {
    set(fetchedAssetToUsdPrice, price.toFixed());
  }

  if (!get(isCurrentCurrencyUsd)) {
    const currentCurrency = get(currencySymbol);

    price = await getHistoricPrice({
      timestamp,
      fromAsset: assetVal,
      toAsset: currentCurrency
    });

    if (price.gt(0)) {
      set(fetchedAssetToFiatPrice, price.toFixed());
    }
  }
};

watch([datetime, asset], async () => {
  await fetchHistoricPrices();
});

watch(fetchedAssetToUsdPrice, price => {
  set(assetToUsdPrice, price);
  onAssetToUsdPriceChange(true);
});

watch(assetToUsdPrice, () => {
  onAssetToUsdPriceChange();
});

watch(usdValue, () => {
  onUsdValueChange();
});

watch(fetchedAssetToFiatPrice, price => {
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
    onAssetToUsdPriceChange();
    onUsdValueChange();
  } else {
    onAssetToFiatPriceChanged();
    onFiatValueChange();
  }
});

const submitPrice = async (
  payload: NewHistoryEventPayload
): Promise<ActionStatus<ValidationErrors | string>> => {
  const assetVal = get(asset);
  const timestamp = convertToTimestamp(
    get(datetime),
    DateFormat.DateMonthYearHourMinuteSecond
  );

  try {
    if (get(isCurrentCurrencyUsd)) {
      if (get(assetToUsdPrice) !== get(fetchedAssetToUsdPrice)) {
        await savePrice({
          fromAsset: assetVal,
          toAsset: CURRENCY_USD,
          timestamp,
          price: get(assetToUsdPrice)
        });
      }
    } else if (get(assetToFiatPrice) !== get(fetchedAssetToFiatPrice)) {
      await savePrice({
        fromAsset: assetVal,
        toAsset: get(currencySymbol),
        timestamp,
        price: get(assetToFiatPrice)
      });
    }

    return { success: true };
  } catch (e: any) {
    let message: ValidationErrors | string = e.message;
    if (e instanceof ApiValidationError) {
      message = e.getValidationErrors(payload);
    }
    return { success: false, message };
  }
};

const reset = () => {
  set(fetchedAssetToUsdPrice, '');
  set(fetchedAssetToFiatPrice, '');
};

defineExpose({
  submitPrice,
  reset
});
</script>

<template>
  <div>
    <div v-if="v$" class="grid md:grid-cols-2 gap-4">
      <AssetSelect
        v-model="assetModel"
        outlined
        required
        :disabled="disableAsset"
        data-cy="asset"
        :error-messages="disableAsset ? [''] : toMessages(v$.asset)"
        @blur="v$.asset.$touch()"
      />
      <AmountInput
        v-model="amountModel"
        outlined
        required
        data-cy="amount"
        :label="t('common.amount')"
        :error-messages="toMessages(v$.amount)"
        @blur="v$.amount.$touch()"
      />
    </div>

    <TwoFieldsAmountInput
      v-if="isCurrentCurrencyUsd"
      class="mb-5"
      :primary-value.sync="assetToUsdPrice"
      :secondary-value.sync="usdValueModel"
      :loading="fetching"
      :disabled="fetching"
      :label="{
        primary: t('transactions.events.form.asset_price.label', {
          symbol: currencySymbol
        }),
        secondary: t('common.value_in_symbol', {
          symbol: currencySymbol
        })
      }"
      :error-messages="{
        primary: toMessages(v$.usdValue),
        secondary: toMessages(v$.usdValue)
      }"
      :hint="t('transactions.events.form.asset_price.hint')"
      @update:reversed="fiatValueFocused = $event"
    />

    <TwoFieldsAmountInput
      v-else
      class="mb-5"
      :primary-value.sync="assetToFiatPrice"
      :secondary-value.sync="fiatValue"
      :loading="fetching"
      :disabled="fetching"
      :label="{
        primary: t('transactions.events.form.asset_price.label', {
          symbol: currencySymbol
        }),
        secondary: t('common.value_in_symbol', {
          symbol: currencySymbol
        })
      }"
      @update:reversed="fiatValueFocused = $event"
    />
  </div>
</template>
