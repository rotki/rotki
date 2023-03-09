<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { type ComputedRef } from 'vue';
import {
  HistoryEventSubType,
  type HistoryEventType
} from '@rotki/common/lib/history/tx-events';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { type Writeable } from '@/types';
import { CURRENCY_USD } from '@/types/currencies';
import {
  type EthTransactionEntry,
  type EthTransactionEvent,
  type NewEthTransactionEvent
} from '@/types/history/tx';
import { TaskType } from '@/types/task-type';
import {
  One,
  Zero,
  bigNumberify,
  bigNumberifyFromRef
} from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { useEventTypeData } from '@/utils/history';
import { toMessages } from '@/utils/validation-errors';
import { type ActionDataEntry } from '@/types/action';
import { transactionEventTypeMapping } from '@/data/transaction-event-mapping';
import { isValidEthAddress } from '@/utils/text';
import { useHistoryStore } from '@/store/history';

const props = withDefaults(
  defineProps<{
    value?: boolean;
    edit?: EthTransactionEvent | null;
    transaction?: EthTransactionEntry | null;
  }>(),
  {
    value: false,
    edit: null,
    transaction: null
  }
);

const emit = defineEmits<{ (e: 'input', valid: boolean): void }>();
const { t } = useI18n();
const { edit, transaction } = toRefs(props);

const { isTaskRunning } = useTaskStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { exchangeRate, getHistoricPrice } = useBalancePricesStore();
const { getEventTypeData } = useEventTypeData();
const { historyEventTypeData, historyEventSubTypeData } =
  useHistoryEventTypeData();

const lastLocation = useLocalStorage(
  'rotki.ledger_action.location',
  TRADE_LOCATION_EXTERNAL
);

const identifier = ref<number | null>(null);
const eventIdentifier = ref<string>('');
const sequenceIndex = ref<string>('');
const datetime = ref<string>('');
const location = ref<string>('');
const eventType = ref<string>('');
const eventSubtype = ref<string>('');
const transactionEventType = ref<string | null>();
const asset = ref<string>('');
const amount = ref<string>('');
const fiatValue = ref<string>('');
const locationLabel = ref<string>('');
const notes = ref<string>('');
const counterparty = ref<string>('');

const rate = ref<string>('');
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
    required: helpers.withMessage(
      t(
        'transactions.events.form.counterparty.validation.non_empty'
      ).toString(),
      required
    ),
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
    usdValue: fiatValue,
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
  set(eventIdentifier, get(transaction)?.txHash || '');
  set(sequenceIndex, '0');
  set(
    datetime,
    convertFromTimestamp(get(transaction)?.timestamp || dayjs().unix(), true)
  );
  set(location, '');
  set(eventType, '');
  set(eventSubtype, '');
  set(asset, '');
  set(amount, '0');
  set(fiatValue, '0');
  set(location, get(lastLocation));
  set(notes, '');
  set(counterparty, '');
  set(rate, '');
  set(errorMessages, {});
};

const fiatExchangeRate = computed<BigNumber>(() => {
  return get(exchangeRate(get(currencySymbol))) ?? One;
});

const setEditMode = async () => {
  const editVal = get(edit);
  if (!editVal) {
    reset();
    return;
  }

  const event: EthTransactionEvent = editVal;

  const convertedFiatValue =
    get(currencySymbol) === CURRENCY_USD
      ? event.balance.usdValue.toFixed()
      : event.balance.usdValue.multipliedBy(get(fiatExchangeRate)).toFixed();

  set(identifier, event.identifier ?? null);
  set(eventIdentifier, event.eventIdentifier);
  set(sequenceIndex, event.sequenceIndex?.toString() ?? '');
  set(datetime, convertFromTimestamp(event.timestamp, true));
  set(location, event.location);
  set(eventType, event.eventType);
  set(eventSubtype, event.eventSubtype || HistoryEventSubType.NONE);
  set(asset, event.asset);
  set(amount, event.balance.amount.toFixed());
  set(fiatValue, convertedFiatValue);
  set(locationLabel, event.locationLabel ?? '');
  set(notes, event.notes ?? '');
  set(counterparty, event.counterparty ?? '');

  await fetchPrice();
};

const { setMessage } = useMessageStore();

const { editTransactionEvent, addTransactionEvent } = useTransactions();

const save = async (): Promise<boolean> => {
  const numericAmount = get(bigNumberifyFromRef(amount));
  const numericFiatValue = get(bigNumberifyFromRef(fiatValue));

  const convertedUsdValue =
    get(currencySymbol) === CURRENCY_USD
      ? numericFiatValue
      : numericFiatValue.dividedBy(get(fiatExchangeRate));

  const transactionEventPayload: Writeable<NewEthTransactionEvent> = {
    eventIdentifier: get(eventIdentifier),
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp: convertToTimestamp(get(datetime)),
    location: get(location),
    eventType: get(eventType) as HistoryEventType,
    eventSubtype: get(eventSubtype) as HistoryEventSubType,
    asset: get(asset),
    balance: {
      amount: numericAmount.isNaN() ? Zero : numericAmount,
      usdValue: convertedUsdValue.isNaN() ? Zero : convertedUsdValue
    },
    locationLabel: get(locationLabel) ? get(locationLabel) : undefined,
    notes: get(notes) ? get(notes) : undefined,
    counterparty: get(counterparty) ? get(counterparty) : undefined
  };

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

const updateUsdValue = () => {
  if (get(amount) && get(rate)) {
    set(
      fiatValue,
      bigNumberify(get(amount))
        .multipliedBy(bigNumberify(get(rate)))
        .toFixed()
    );
  }
};

const fetchPrice = async () => {
  if ((get(fiatValue) && get(edit)) || !get(datetime) || !get(asset)) {
    return;
  }

  const timestamp = convertToTimestamp(get(datetime));
  const fromAsset = get(asset);
  const toAsset = get(currencySymbol);

  const rateFromHistoricPrice = await getHistoricPrice({
    timestamp,
    fromAsset,
    toAsset
  });

  if (rateFromHistoricPrice.gt(0)) {
    set(rate, rateFromHistoricPrice.toFixed());
    updateUsdValue();
  }
};

watch(edit, async () => {
  await setEditMode();
});

watch([datetime, asset], async () => {
  await fetchPrice();
});

watch(amount, () => {
  updateUsdValue();
});

watch(transaction, transaction => {
  set(eventIdentifier, transaction?.txHash || '');
});

watch(location, (location: string) => {
  if (location) {
    set(lastLocation, location);
  }
});

watch([eventType, eventSubtype], ([type, subType]) => {
  const typeData = getEventTypeData(
    { eventType: type, eventSubtype: subType },
    false
  );

  set(transactionEventType, typeData.label);

  if (
    subType &&
    !get(historyEventSubTypeFilteredData)
      .map(({ identifier }) => identifier)
      .includes(subType)
  ) {
    set(eventSubtype, '');
  }
});

watch(v$, ({ $invalid }) => {
  emit('input', !$invalid);
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

    return allData.filter(data => subTypeMapping.includes(data.identifier));
  });

const { counterparties } = storeToRefs(useHistoryStore());
</script>
<template>
  <v-form
    :value="value"
    data-cy="transaction-event-form"
    class="transaction-event-form"
  >
    <location-selector
      v-model="location"
      class="pt-1"
      required
      outlined
      data-cy="location"
      :label="t('common.location')"
      :error-messages="toMessages(v$.location)"
      @blur="v$.location.$touch()"
    />

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

    <v-row
      align="center"
      :class="
        $vuetify.breakpoint.mdAndUp
          ? 'transaction-event-form__amount-wrapper'
          : null
      "
    >
      <v-col cols="12" md="4">
        <asset-select
          v-model="asset"
          outlined
          required
          data-cy="asset"
          :error-messages="toMessages(v$.asset)"
          @blur="v$.asset.$touch()"
        />
      </v-col>

      <v-col cols="12" md="4">
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

      <v-col cols="12" md="4">
        <amount-input
          v-model="fiatValue"
          outlined
          required
          data-cy="fiatValue"
          :loading="fetching"
          :label="
            t('common.value_in_symbol', {
              symbol: currencySymbol
            })
          "
          :error-messages="toMessages(v$.usdValue)"
          @blur="v$.usdValue.$touch()"
        >
          <template #append>
            <div class="pt-1">
              <value-accuracy-hint />
            </div>
          </template>
        </amount-input>
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
          :error-messages="v$.counterparty.$errors.map(e => e.$message)"
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
