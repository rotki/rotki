<template>
  <v-form
    :value="value"
    data-cy="transaction-event-form"
    class="transaction-event-form"
    @input="input"
  >
    <location-selector
      v-model="location"
      class="pt-1"
      required
      outlined
      data-cy="location"
      :rules="locationRules"
      :label="$t('common.location')"
      :error-messages="errorMessages['location']"
      @focus="delete errorMessages['location']"
    />

    <date-time-picker
      v-model="datetime"
      outlined
      :label="$t('transactions.events.form.datetime.label')"
      persistent-hint
      required
      seconds
      limit-now
      data-cy="datetime"
      :hint="$t('transactions.events.form.datetime.hint')"
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
          :rules="assetRules"
          :error-messages="errorMessages['asset']"
          @focus="delete errorMessages['asset']"
        />
      </v-col>

      <v-col cols="12" md="4">
        <amount-input
          v-model="amount"
          outlined
          required
          data-cy="amount"
          :rules="amountRules"
          :label="$t('common.amount')"
          :error-messages="errorMessages['amount']"
          @focus="delete errorMessages['amount']"
        />
      </v-col>

      <v-col cols="12" md="4">
        <amount-input
          v-model="fiatValue"
          outlined
          required
          data-cy="fiatValue"
          :rules="fiatValueRules"
          :loading="fetching"
          :label="
            $t('common.value_in_symbol', {
              symbol: currencySymbol
            })
          "
          :error-messages="errorMessages['usdValue']"
          @focus="delete errorMessages['usdValue']"
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
          :label="$t('transactions.events.form.event_type.label')"
          :items="historyEventTypeData"
          item-value="identifier"
          item-text="label"
          data-cy="eventType"
          :rules="eventTypeRules"
          :error-messages="errorMessages['eventType']"
          @focus="delete errorMessages['eventType']"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-autocomplete
          v-model="eventSubtype"
          outlined
          required
          :label="$t('transactions.events.form.event_subtype.label')"
          :items="historyEventSubTypeData"
          item-value="identifier"
          item-text="label"
          data-cy="eventSubtype"
          :rules="eventSubtypeRules"
          :error-messages="errorMessages['eventSubtype']"
          @focus="delete errorMessages['eventSubtype']"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="transactionEventType"
          outlined
          required
          disabled
          :label="$t('transactions.events.form.transaction_event_type.label')"
        />
      </v-col>
      <v-col cols="12" md="4">
        <amount-input
          v-model="sequenceIndex"
          outlined
          required
          integer
          data-cy="sequenceIndex"
          :rules="sequenceIndexRules"
          :label="$t('transactions.events.form.sequence_index.label')"
          :error-messages="errorMessages['sequenceIndex']"
          @focus="delete errorMessages['sequenceIndex']"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="locationLabel"
          outlined
          data-cy="locationLabel"
          :label="$t('transactions.events.form.location_label.label')"
          :error-messages="errorMessages['locationLabel']"
          @focus="delete errorMessages['locationLabel']"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="counterparty"
          outlined
          data-cy="counterparty"
          :label="$t('transactions.events.form.counterparty.label')"
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
      :label="$t('transactions.events.form.notes.label')"
      :hint="$t('transactions.events.form.notes.hint')"
      :error-messages="errorMessages['notes']"
      @focus="delete errorMessages['notes']"
    />
  </v-form>
</template>
<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set, useLocalStorage } from '@vueuse/core';
import dayjs from 'dayjs';
import { storeToRefs } from 'pinia';
import ValueAccuracyHint from '@/components/helper/hint/ValueAccuracyHint.vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import { CURRENCY_USD } from '@/data/currencies';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import i18n from '@/i18n';
import { convertKeys } from '@/services/axios-tranformers';
import { deserializeApiErrorMessage } from '@/services/converters';
import {
  EthTransactionEvent,
  NewEthTransactionEvent
} from '@/services/history/types';
import { useBalancePricesStore } from '@/store/balances/prices';
import {
  historyEventSubTypeData,
  historyEventTypeData
} from '@/store/history/consts';
import {
  EthTransactionEntry,
  EthTransactionEventEntry
} from '@/store/history/types';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { Writeable } from '@/types';
import { TaskType } from '@/types/task-type';
import { HistoryEventSubType, HistoryEventType } from '@/types/transaction';
import { bigNumberifyFromRef, One, Zero } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { getEventTypeData } from '@/utils/history';

const TransactionEventForm = defineComponent({
  name: 'TransactionEventForm',
  components: { ValueAccuracyHint, LocationSelector },
  props: {
    value: { required: false, type: Boolean, default: false },
    edit: {
      required: false,
      type: Object as PropType<EthTransactionEvent>,
      default: null
    },
    transaction: {
      required: false,
      type: Object as PropType<EthTransactionEntry>,
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
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { edit, transaction } = toRefs(props);
    const { saveData } = props;

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

    const locationRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('transactions.events.form.location.validation.non_empty')
          .toString()
    ];

    const assetRules = [
      (v: string) =>
        !!v ||
        i18n.t('transactions.events.form.asset.validation.non_empty').toString()
    ];

    const amountRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('transactions.events.form.amount.validation.non_empty')
          .toString()
    ];

    const fiatValueRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('transactions.events.form.fiat_value.validation.non_empty', {
            currency: get(currencySymbol)
          })
          .toString()
    ];

    const sequenceIndexRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('transactions.events.form.sequence_index.validation.non_empty')
          .toString()
    ];

    const eventTypeRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('transactions.events.form.event_type.validation.non_empty')
          .toString()
    ];

    const eventSubtypeRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('transactions.events.form.event_subtype.validation.non_empty')
          .toString()
    ];

    const fetching = isTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

    const reset = () => {
      set(identifier, null);
      set(eventIdentifier, get(transaction)?.txHash || '');
      set(sequenceIndex, '0');
      set(
        datetime,
        convertFromTimestamp(
          get(transaction)?.timestamp || dayjs().unix(),
          true
        )
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

    const setEditMode = () => {
      if (!get(edit)) {
        reset();
        return;
      }

      const event: EthTransactionEvent = get(edit);

      const convertedFiatValue =
        get(currencySymbol) === CURRENCY_USD
          ? event.balance.usdValue.toFixed()
          : event.balance.usdValue
              .multipliedBy(get(fiatExchangeRate))
              .toFixed();

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

      fetchPrice();
    };

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

      const result = !get(identifier)
        ? await saveData(transactionEventPayload)
        : await saveData({
            ...transactionEventPayload,
            identifier: get(identifier)!
          });

      if (result.success) {
        reset();
        return true;
      }

      if (result.message) {
        set(
          errorMessages,
          convertKeys(
            deserializeApiErrorMessage(result.message) ?? {},
            true,
            false
          )
        );
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

    watch(edit, () => {
      setEditMode();
    });

    watch([datetime, asset], () => {
      fetchPrice();
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

    onMounted(() => {
      setEditMode();
    });

    return {
      currencySymbol,
      historyEventTypeData,
      historyEventSubTypeData,
      input,
      sequenceIndex,
      datetime,
      location,
      eventType,
      eventSubtype,
      transactionEventType,
      asset,
      amount,
      fiatValue,
      locationLabel,
      notes,
      counterparty,
      errorMessages,
      locationRules,
      assetRules,
      amountRules,
      fiatValueRules,
      sequenceIndexRules,
      eventTypeRules,
      eventSubtypeRules,
      fetching,
      save,
      reset
    };
  }
});

export type TransactionEventFormInstance = InstanceType<
  typeof TransactionEventForm
>;

export default TransactionEventForm;
</script>
