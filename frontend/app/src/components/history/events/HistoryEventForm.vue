<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { type BigNumber } from '@rotki/common';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { type Writeable } from '@/types';
import { CURRENCY_USD } from '@/types/currencies';
import {
  type EvmHistoryEvent,
  type HistoryEvent,
  type NewEvmHistoryEventPayload
} from '@/types/history/events';
import { TaskType } from '@/types/task-type';
import { toMessages } from '@/utils/validation';
import { type ActionDataEntry } from '@/types/action';
import { type HistoricalPriceFormPayload } from '@/types/prices';

const props = withDefaults(
  defineProps<{
    editableItem?: EvmHistoryEvent | null;
    transaction: EvmHistoryEvent;
  }>(),
  {
    editableItem: null
  }
);

const emit = defineEmits<{ (e: 'input', valid: boolean): void }>();

const { t } = useI18n();

const { editableItem, transaction } = toRefs(props);

const { isTaskRunning } = useTaskStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { getHistoricPrice } = useBalancePricesStore();
const { addHistoricalPrice } = useAssetPricesApi();
const {
  counterparties,
  getEventTypeData,
  historyEventTypesData,
  historyEventSubTypesData,
  historyEventTypeGlobalMapping,
  historyEventTypePerProtocolMapping,
  historyEventProductsMapping
} = useHistoryEventMappings();

const isCurrentCurrencyUsd: ComputedRef<boolean> = computed(
  () => get(currencySymbol) === CURRENCY_USD
);

const lastLocation = useLocalStorage(
  'rotki.ledger_action.location',
  TRADE_LOCATION_EXTERNAL
);

const identifier = ref<number | null>(null);
const sequenceIndex = ref<string>('');
const datetime = ref<string>('');
const location = ref<string>('');
const eventType = ref<string>('');
const eventSubtype = ref<string>('');
const transactionEventType = ref<string | null>();
const asset = ref<string>('');
const amount = ref<string>('');
const assetToUsdPrice = ref<string>('');
const assetToFiatPrice = ref<string>('');
const usdValue = ref<string>('');
const fiatValue = ref<string>('');
const locationLabel = ref<string>('');
const notes = ref<string>('');
const counterparty = ref<string>('');
const product = ref<string>('');

const errorMessages = ref<Record<string, string[]>>({});

const rules = {
  location: {
    required: helpers.withMessage(
      t('transactions.events.form.location.validation.non_empty').toString(),
      required
    )
  },
  asset: {
    required: helpers.withMessage(
      t('transactions.events.form.asset.validation.non_empty').toString(),
      required
    )
  },
  amount: {
    required: helpers.withMessage(
      t('transactions.events.form.amount.validation.non_empty').toString(),
      required
    )
  },
  usdValue: {
    required: helpers.withMessage(
      t('transactions.events.form.fiat_value.validation.non_empty', {
        currency: get(currencySymbol)
      }).toString(),
      required
    )
  },
  sequenceIndex: {
    required: helpers.withMessage(
      t(
        'transactions.events.form.sequence_index.validation.non_empty'
      ).toString(),
      required
    )
  },
  eventType: {
    required: helpers.withMessage(
      t('transactions.events.form.event_type.validation.non_empty').toString(),
      required
    )
  },
  eventSubtype: {
    required: helpers.withMessage(
      t(
        'transactions.events.form.event_subtype.validation.non_empty'
      ).toString(),
      required
    )
  },
  counterparty: {
    isValid: helpers.withMessage(
      t('transactions.events.form.counterparty.validation.valid').toString(),
      (value: string) =>
        !value ||
        get(counterparties).includes(value) ||
        isValidEthAddress(value)
    )
  },
  product: {
    isValid: helpers.withMessage(
      t('transactions.events.form.product.validation.valid').toString(),
      (value: string) =>
        !value || get(historyEventLimitedProducts).includes(value)
    )
  }
};

const { valid, setValidation, setSubmitFunc } = useHistoryEventsForm();

const v$ = setValidation(
  rules,
  {
    location,
    asset,
    amount,
    usdValue,
    sequenceIndex,
    eventType,
    eventSubtype,
    counterparty,
    product
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages
  }
);

const fetching = isTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

const reset = () => {
  set(identifier, null);
  set(sequenceIndex, '0');
  set(
    datetime,
    convertFromTimestamp(get(transaction).timestamp || dayjs().unix(), true)
  );
  set(location, get(transaction).location || get(lastLocation));
  set(locationLabel, get(transaction).locationLabel || '');
  set(eventType, '');
  set(eventSubtype, '');
  set(asset, '');
  set(amount, '0');
  set(usdValue, '0');
  set(notes, '');
  set(counterparty, '');
  set(product, '');
  set(fetchedAssetToUsdPrice, '');
  set(fetchedAssetToFiatPrice, '');
  set(errorMessages, {});
};

const setEditMode = async () => {
  const editVal = get(editableItem);
  if (!editVal) {
    reset();
    return;
  }

  const event: HistoryEvent = editVal;
  set(identifier, event.identifier ?? null);
  set(sequenceIndex, event.sequenceIndex?.toString() ?? '');
  set(datetime, convertFromTimestamp(event.timestamp, true));
  set(location, event.location);
  set(eventType, event.eventType);
  set(eventSubtype, event.eventSubtype || 'none');
  set(asset, event.asset);
  set(amount, event.balance.amount.toFixed());
  set(usdValue, event.balance.usdValue.toFixed());
  set(locationLabel, event.locationLabel ?? '');
  set(notes, event.notes ?? '');
  set(counterparty, event.counterparty ?? '');
  set(product, event.product ?? '');
};

const { setMessage } = useMessageStore();

const { editTransactionEvent, addTransactionEvent } = useHistoryTransactions();
const { resetHistoricalPricesData } = useHistoricCachePriceStore();

const savePrice = async (payload: HistoricalPriceFormPayload) => {
  await addHistoricalPrice(payload);
  await resetHistoricalPricesData([payload]);
};

const save = async (): Promise<boolean> => {
  const timestamp = convertToTimestamp(get(datetime));
  const assetVal = get(asset);
  const { address, txHash } = get(transaction);

  const transactionEventPayload: Writeable<NewEvmHistoryEventPayload> = {
    address,
    txHash,
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp,
    eventType: get(eventType),
    eventSubtype: get(eventSubtype),
    asset: assetVal,
    balance: {
      amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
      usdValue: get(numericUsdValue).isNaN() ? Zero : get(numericUsdValue)
    },
    location: get(location),
    locationLabel: get(locationLabel) || null,
    notes: get(notes) || '',
    counterparty: get(counterparty) || null,
    product: get(product) || null
  };

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

  const id = get(identifier);
  const result = !id
    ? await addTransactionEvent(transactionEventPayload)
    : await editTransactionEvent({
        ...transactionEventPayload,
        identifier: id
      });

  if (result.success) {
    reset();
    return true;
  }

  if (result.message) {
    if (typeof result.message === 'string') {
      setMessage({
        description: result.message
      });
    } else {
      set(errorMessages, result.message);
      await get(v$).$validate();
    }
  }

  return false;
};

setSubmitFunc(save);

const fiatValueFocused = ref<boolean>(false);

const fetchedAssetToUsdPrice: Ref<string> = ref('');
const fetchedAssetToFiatPrice: Ref<string> = ref('');

const numericAmount = bigNumberifyFromRef(amount);
const numericAssetToUsdPrice = bigNumberifyFromRef(assetToUsdPrice);
const numericUsdValue = bigNumberifyFromRef(usdValue);
const numericAssetToFiatPrice = bigNumberifyFromRef(assetToFiatPrice);
const numericFiatValue = bigNumberifyFromRef(fiatValue);

const onAssetToUsdPriceChange = (forceUpdate = false) => {
  if (
    get(amount) &&
    get(assetToUsdPrice) &&
    (!get(fiatValueFocused) || forceUpdate)
  ) {
    set(
      usdValue,
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

  const timestamp = convertToTimestamp(get(datetime));

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

watch(transaction, transaction => {
  set(location, transaction.location || get(lastLocation));
});

watch(location, (location: string) => {
  if (location) {
    set(lastLocation, location);
  }
});

watch(
  [eventType, eventSubtype, counterparty, location],
  ([eventType, eventSubtype, counterparty, location]) => {
    const typeData = get(
      getEventTypeData(
        {
          eventType,
          eventSubtype,
          counterparty,
          location,
          entryType: HistoryEventEntryType.EVM_EVENT
        },
        false
      )
    );
    set(transactionEventType, typeData.label);
  }
);

watch(v$, ({ $invalid }) => {
  emit('input', !$invalid);
});

watch(editableItem, setEditMode);
onMounted(setEditMode);

const historyEventSubTypeFilteredData: ComputedRef<ActionDataEntry[]> =
  computed(() => {
    const eventTypeVal = get(eventType);
    const allData = get(historyEventSubTypesData);
    const globalMapping = get(historyEventTypeGlobalMapping);
    const perProtocolMapping = get(historyEventTypePerProtocolMapping);
    const counterpartyVal = get(counterparty);
    const locationVal = get(location);

    if (!eventTypeVal) {
      return allData;
    }

    const globalMappingKeys = Object.keys(globalMapping[eventTypeVal]);
    let perProtocolMappingKeys: string[] = [];

    if (locationVal && counterpartyVal) {
      const perProtocolMappingObj =
        perProtocolMapping?.[locationVal]?.[counterpartyVal]?.[eventTypeVal];
      if (perProtocolMappingObj) {
        perProtocolMappingKeys = Object.keys(perProtocolMappingObj);
      }
    }

    return allData.filter(
      (data: ActionDataEntry) =>
        globalMappingKeys.includes(data.identifier) ||
        perProtocolMappingKeys.includes(data.identifier)
    );
  });

const historyEventLimitedProducts: ComputedRef<string[]> = computed(() => {
  const counterpartyVal = get(counterparty);
  const mapping = get(historyEventProductsMapping);

  if (!counterpartyVal) {
    return [];
  }

  return mapping[counterpartyVal] ?? [];
});

watch(historyEventLimitedProducts, products => {
  const selected = get(product);
  if (!products.includes(selected)) {
    set(product, '');
  }
});

const evmEvent = isEvmEventRef(transaction);
const { mdAndUp } = useDisplay();
</script>

<template>
  <VForm
    :value="valid"
    data-cy="transaction-event-form"
    class="transaction-event-form"
  >
    <VRow class="pt-1" align="center">
      <VCol cols="12" md="6">
        <LocationSelector
          v-model="location"
          required
          outlined
          :disabled="!!evmEvent"
          data-cy="location"
          :label="t('common.location')"
          :error-messages="toMessages(v$.location)"
          @blur="v$.location.$touch()"
        />
      </VCol>
      <VCol cols="12" md="6">
        <DateTimePicker
          v-model="datetime"
          outlined
          :label="t('transactions.events.form.datetime.label')"
          persistent-hint
          required
          seconds
          limit-now
          data-cy="datetime"
          :hint="t('transactions.events.form.datetime.hint')"
          :error-messages="errorMessages['datetime']"
        />
      </VCol>
    </VRow>
    <VRow :class="mdAndUp ? 'transaction-event-form__amount-wrapper' : null">
      <VCol cols="12" md="6">
        <AssetSelect
          v-model="asset"
          outlined
          required
          data-cy="asset"
          :error-messages="toMessages(v$.asset)"
          @blur="v$.asset.$touch()"
        />
      </VCol>

      <VCol cols="12" md="6">
        <AmountInput
          v-model="amount"
          outlined
          required
          data-cy="amount"
          :label="t('common.amount')"
          :error-messages="toMessages(v$.amount)"
          @blur="v$.amount.$touch()"
        />
      </VCol>

      <VCol cols="12">
        <TwoFieldsAmountInput
          v-if="isCurrentCurrencyUsd"
          class="mb-5"
          :primary-value.sync="assetToUsdPrice"
          :secondary-value.sync="usdValue"
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
      </VCol>
    </VRow>

    <VDivider class="mb-6 mt-6" />

    <VRow>
      <VCol cols="12" md="4">
        <VAutocomplete
          v-model="eventType"
          outlined
          required
          :label="t('transactions.events.form.event_type.label')"
          :items="historyEventTypesData"
          item-value="identifier"
          item-text="label"
          data-cy="eventType"
          :error-messages="toMessages(v$.eventType)"
          @blur="v$.eventType.$touch()"
        />
      </VCol>
      <VCol cols="12" md="4">
        <VAutocomplete
          v-model="eventSubtype"
          outlined
          required
          :label="t('transactions.events.form.event_subtype.label')"
          :items="historyEventSubTypeFilteredData"
          item-value="identifier"
          item-text="label"
          data-cy="eventSubtype"
          :error-messages="toMessages(v$.eventSubtype)"
          @blur="v$.eventSubtype.$touch()"
        />
      </VCol>
      <VCol cols="12" md="4">
        <VTextField
          v-model="transactionEventType"
          outlined
          required
          disabled
          :label="t('transactions.events.form.transaction_event_type.label')"
        />
      </VCol>

      <VDivider class="mb-6 mt-6" />

      <VCol cols="12" md="6">
        <VTextField
          v-model="locationLabel"
          :disabled="!!evmEvent"
          outlined
          data-cy="locationLabel"
          :label="t('transactions.events.form.location_label.label')"
          :error-messages="errorMessages['locationLabel']"
        />
      </VCol>

      <VCol cols="12" md="6">
        <AmountInput
          v-model="sequenceIndex"
          outlined
          required
          integer
          data-cy="sequenceIndex"
          :label="t('transactions.events.form.sequence_index.label')"
          :error-messages="toMessages(v$.sequenceIndex)"
          @blur="v$.sequenceIndex.$touch()"
        />
      </VCol>

      <VCol cols="12" md="6">
        <ComboboxWithCustomInput
          v-model="counterparty"
          outlined
          required
          auto-select-first
          :label="t('transactions.events.form.counterparty.label')"
          :items="counterparties"
          data-cy="counterparty"
          :error-messages="toMessages(v$.counterparty)"
          @blur="v$.counterparty.$touch()"
        />
      </VCol>

      <VCol cols="12" md="6">
        <VAutocomplete
          v-model="product"
          clearable
          outlined
          required
          auto-select-first
          :disabled="historyEventLimitedProducts.length === 0"
          :label="t('transactions.events.form.product.label')"
          :items="historyEventLimitedProducts"
          data-cy="product"
          :error-messages="toMessages(v$.product)"
          @blur="v$.product.$touch()"
        />
      </VCol>
    </VRow>

    <VDivider class="mb-6 mt-2" />

    <VTextarea
      v-model="notes"
      prepend-inner-icon="mdi-text-box-outline"
      persistent-hint
      outlined
      data-cy="notes"
      :label="t('transactions.events.form.notes.label')"
      :hint="t('transactions.events.form.notes.hint')"
      :error-messages="errorMessages['notes']"
    />
  </VForm>
</template>
