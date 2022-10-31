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
      :error-messages="v$.location.$errors.map(e => e.$message)"
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
      @focus="delete errorMessages['datetime']"
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
          :error-messages="v$.asset.$errors.map(e => e.$message)"
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
          :error-messages="v$.amount.$errors.map(e => e.$message)"
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
          :error-messages="v$.usdValue.$errors.map(e => e.$message)"
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
          :error-messages="v$.eventType.$errors.map(e => e.$message)"
          @blur="v$.eventType.$touch()"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-autocomplete
          v-model="eventSubtype"
          outlined
          required
          :label="t('transactions.events.form.event_subtype.label')"
          :items="historyEventSubTypeData"
          item-value="identifier"
          item-text="label"
          data-cy="eventSubtype"
          :error-messages="v$.eventSubtype.$errors.map(e => e.$message)"
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
          :error-messages="v$.sequenceIndex.$errors.map(e => e.$message)"
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
          @focus="delete errorMessages['locationLabel']"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="counterparty"
          outlined
          data-cy="counterparty"
          :label="t('transactions.events.form.counterparty.label')"
          :error-messages="errorMessages['counterparty']"
          @focus="delete errorMessages['counterparty']"
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
      @focus="delete errorMessages['notes']"
    />
  </v-form>
</template>
<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { PropType } from 'vue';
import ValueAccuracyHint from '@/components/helper/hint/ValueAccuracyHint.vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { convertKeys } from '@/services/axios-tranformers';
import { deserializeApiErrorMessage } from '@/services/converters';
import { useBalancePricesStore } from '@/store/balances/prices';
import {
  historyEventSubTypeData,
  historyEventTypeData
} from '@/store/history/consts';
import {
  EthTransactionEntry,
  EthTransactionEventEntry
} from '@/store/history/types';
import { useMessageStore } from '@/store/message';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { Writeable } from '@/types';
import { CURRENCY_USD } from '@/types/currencies';
import {
  EthTransactionEvent,
  NewEthTransactionEvent
} from '@/types/history/tx';
import { TaskType } from '@/types/task-type';
import { HistoryEventSubType, HistoryEventType } from '@/types/transaction';
import { bigNumberifyFromRef, One, Zero } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { getEventTypeData } from '@/utils/history';

const props = defineProps({
  value: { required: false, type: Boolean, default: false },
  edit: {
    required: false,
    type: Object as PropType<EthTransactionEvent | null>,
    default: null
  },
  transaction: {
    required: false,
    type: Object as PropType<EthTransactionEntry | null>,
    default: null
  },
  saveData: {
    required: true,
    type: Function as PropType<
      (
        event: NewEthTransactionEvent | EthTransactionEventEntry
      ) => Promise<ActionStatus>
    >
  }
});

const emit = defineEmits<{ (e: 'input', valid: boolean): void }>();
const { t } = useI18n();
const { edit, transaction, saveData } = toRefs(props);

const input = (valid: boolean) => emit('input', valid);

const { isTaskRunning } = useTasks();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { exchangeRate, getHistoricPrice } = useBalancePricesStore();

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
const errorMessages = ref<{ [field: string]: string[] }>({});

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
    eventSubtype
  },
  { $externalResults: errorMessages }
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

  const save = get(saveData);
  const result = !get(identifier)
    ? await save(transactionEventPayload)
    : await save({
        ...transactionEventPayload,
        identifier: get(identifier)!
      });

  if (result.success) {
    reset();
    return true;
  }

  if (result.message) {
    const errorFields = deserializeApiErrorMessage(result.message);
    if (errorFields) {
      set(errorMessages, convertKeys(errorFields, true, false));
    } else {
      setMessage({
        description: result.message
      });
    }
  }

  return false;
};

const updateUsdValue = () => {
  if (get(amount) && get(rate)) {
    set(
      fiatValue,
      new BigNumber(get(amount))
        .multipliedBy(new BigNumber(get(rate)))
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

watch([eventType, eventSubtype], ([eventType, eventSubtype]) => {
  const typeData = getEventTypeData({ eventType, eventSubtype }, false);
  set(transactionEventType, typeData.label);
});

watch(v$, ({ $invalid }) => {
  input(!$invalid);
});

onMounted(async () => {
  await setEditMode();
});

defineExpose({
  save,
  reset
});
</script>
