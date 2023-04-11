<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { type ComputedRef } from 'vue';
import {
  HistoryEventSubType,
  type HistoryEventType
} from '@rotki/common/lib/history/tx-events';
import { type BigNumber } from '@rotki/common';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { type Writeable } from '@/types';
import { CURRENCY_USD } from '@/types/currencies';
import {
  type HistoryEvent,
  type HistoryEventEntry,
  type NewHistoryEvent
} from '@/types/history/tx';
import { TaskType } from '@/types/task-type';
import { Zero, bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { useEventTypeData } from '@/utils/history';
import { toMessages } from '@/utils/validation-errors';
import { type ActionDataEntry } from '@/types/action';
import { transactionEventTypeMapping } from '@/data/transaction-event-mapping';
import { isValidEthAddress, isValidTxHash } from '@/utils/text';
import { useHistoryStore } from '@/store/history';

const props = withDefaults(
  defineProps<{
    value?: boolean;
    edit?: HistoryEvent | null;
    transaction: HistoryEventEntry;
  }>(),
  {
    value: false,
    edit: null
  }
);

const emit = defineEmits<{ (e: 'input', valid: boolean): void }>();
const { t } = useI18n();
const { edit, transaction } = toRefs(props);

const { isTaskRunning } = useTaskStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { getHistoricPrice } = useBalancePricesStore();
const { addHistoricalPrice } = useAssetPricesApi();
const { getEventTypeData } = useEventTypeData();
const { historyEventTypeData, historyEventSubTypeData } =
  useHistoryEventTypeData();

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
        get(counterparties).includes(value) || isValidEthAddress(value)
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    location,
    asset,
    amount,
    usdValue,
    sequenceIndex,
    eventType,
    eventSubtype,
    counterparty
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
  set(eventType, '');
  set(eventSubtype, '');
  set(asset, '');
  set(amount, '0');
  set(usdValue, '0');
  set(notes, '');
  set(counterparty, '');
  set(fetchedAssetToUsdPrice, '');
  set(fetchedAssetToFiatPrice, '');
  set(errorMessages, {});
};

const setEditMode = async () => {
  const editVal = get(edit);
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
  set(eventSubtype, event.eventSubtype || HistoryEventSubType.NONE);
  set(asset, event.asset);
  set(amount, event.balance.amount.toFixed());
  set(usdValue, event.balance.usdValue.toFixed());
  set(locationLabel, event.locationLabel ?? '');
  set(notes, event.notes ?? '');
  set(counterparty, event.counterparty ?? '');
};

const { setMessage } = useMessageStore();

const { editTransactionEvent, addTransactionEvent } = useHistoryEvents();

const save = async (): Promise<boolean> => {
  const timestamp = convertToTimestamp(get(datetime));
  const assetVal = get(asset);

  const transactionEventPayload: Writeable<NewHistoryEvent> = {
    eventIdentifier: get(eventIdentifier),
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp,
    location: get(location),
    eventType: get(eventType) as HistoryEventType,
    eventSubtype: get(eventSubtype) as HistoryEventSubType,
    asset: assetVal,
    balance: {
      amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
      usdValue: get(numericUsdValue).isNaN() ? Zero : get(numericUsdValue)
    },
    locationLabel: get(locationLabel) || undefined,
    notes: get(notes) || undefined,
    counterparty: get(counterparty) || undefined
  };

  if (get(isCurrentCurrencyUsd)) {
    if (get(assetToUsdPrice) !== get(fetchedAssetToUsdPrice)) {
      await addHistoricalPrice({
        fromAsset: assetVal,
        toAsset: CURRENCY_USD,
        timestamp,
        price: get(assetToUsdPrice)
      });
    }
  } else if (get(assetToFiatPrice) !== get(fetchedAssetToFiatPrice)) {
    await addHistoricalPrice({
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

  let price: BigNumber = Zero;
  price = await getHistoricPrice({
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

const eventIdentifier: ComputedRef<string> = computed(
  () => get(transaction).eventIdentifier
);

const isTx: ComputedRef<boolean> = computed(() =>
  isValidTxHash(get(eventIdentifier))
);

watch(transaction, transaction => {
  set(location, transaction.location || get(lastLocation));
});

watch(location, (location: string) => {
  if (location) {
    set(lastLocation, location);
  }
});

watch([eventType, eventSubtype], ([eventType, eventSubtype]) => {
  const typeData = getEventTypeData({ eventType, eventSubtype }, false);
  set(transactionEventType, typeData.label);
});

watch(v$, ({ $invalid }) => {
  emit('input', !$invalid);
});

watch(edit, async () => {
  await setEditMode();
});

onMounted(async () => {
  await setEditMode();
});

defineExpose({
  save,
  reset
});

const historyEventSubTypeFilteredData: ComputedRef<ActionDataEntry[]> =
  computed(() => {
    const eventTypeVal = get(eventType);
    const allData = get(historyEventSubTypeData);
    const mapping = transactionEventTypeMapping;

    if (!eventTypeVal) {
      return allData;
    }

    const subTypeMapping = Object.keys(mapping[eventTypeVal]);

    return allData.filter((data: ActionDataEntry) =>
      subTypeMapping.includes(data.identifier)
    );
  });

const { counterparties } = storeToRefs(useHistoryStore());
</script>
<template>
  <v-form
    :value="value"
    data-cy="transaction-event-form"
    class="transaction-event-form"
  >
    <v-row class="pt-1" align="center">
      <v-col cols="12" md="6">
        <location-selector
          v-model="location"
          required
          outlined
          :disabled="isTx"
          data-cy="location"
          :label="t('common.location')"
          :error-messages="toMessages(v$.location)"
          @blur="v$.location.$touch()"
        />
      </v-col>
      <v-col cols="12" md="6">
        <date-time-picker
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
      </v-col>
    </v-row>
    <v-row
      :class="
        $vuetify.breakpoint.mdAndUp
          ? 'transaction-event-form__amount-wrapper'
          : null
      "
    >
      <v-col cols="12" md="6">
        <asset-select
          v-model="asset"
          outlined
          required
          data-cy="asset"
          :error-messages="toMessages(v$.asset)"
          @blur="v$.asset.$touch()"
        />
      </v-col>

      <v-col cols="12" md="6">
        <amount-input
          v-model="amount"
          outlined
          required
          data-cy="amount"
          :label="t('common.amount')"
          :error-messages="toMessages(v$.amount)"
          @blur="v$.amount.$touch()"
        />
      </v-col>

      <v-col cols="12">
        <two-fields-amount-input
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

        <two-fields-amount-input
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
      </v-col>
    </v-row>

    <v-divider class="mb-6 mt-2" />

    <v-row>
      <v-col cols="12" md="4">
        <v-autocomplete
          v-model="eventType"
          outlined
          required
          :label="t('transactions.events.form.event_type.label')"
          :items="historyEventTypeData"
          item-value="identifier"
          item-text="label"
          data-cy="eventType"
          :error-messages="toMessages(v$.eventType)"
          @blur="v$.eventType.$touch()"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-autocomplete
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
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="transactionEventType"
          outlined
          required
          disabled
          :label="t('transactions.events.form.transaction_event_type.label')"
        />
      </v-col>
      <v-col cols="12" md="4">
        <amount-input
          v-model="sequenceIndex"
          outlined
          required
          integer
          data-cy="sequenceIndex"
          :label="t('transactions.events.form.sequence_index.label')"
          :error-messages="toMessages(v$.sequenceIndex)"
          @blur="v$.sequenceIndex.$touch()"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="locationLabel"
          outlined
          data-cy="locationLabel"
          :label="t('transactions.events.form.location_label.label')"
          :error-messages="errorMessages['locationLabel']"
        />
      </v-col>
      <v-col cols="12" md="4">
        <combobox-with-custom-input
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
      </v-col>
    </v-row>

    <v-textarea
      v-model="notes"
      prepend-inner-icon="mdi-text-box-outline"
      persistent-hint
      outlined
      data-cy="notes"
      :label="t('transactions.events.form.notes.label')"
      :hint="t('transactions.events.form.notes.hint')"
      :error-messages="errorMessages['notes']"
    />
  </v-form>
</template>
