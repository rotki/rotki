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
      :label="$t('transactions.events.form.location.label')"
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
          :label="$t('transactions.events.form.amount.label')"
          :error-messages="errorMessages['amount']"
          @focus="delete errorMessages['amount']"
        />
      </v-col>

      <v-col cols="12" md="4">
        <amount-input
          v-model="usdValue"
          outlined
          required
          data-cy="usdValue"
          :rules="usdValueRules"
          :loading="fetching"
          :label="$t('transactions.events.form.usd_value.label')"
          :error-messages="errorMessages['usdValue']"
          @focus="delete errorMessages['usdValue']"
        />
      </v-col>
    </v-row>

    <v-divider class="mb-6 mt-2" />

    <v-row>
      <v-col cols="12" md="4">
        <v-autocomplete
          v-model="eventType"
          outlined
          :label="$t('transactions.events.form.event_type.label')"
          :items="historyEventTypeData"
          item-value="identifier"
          item-text="label"
          data-cy="eventType"
          :error-messages="errorMessages['eventType']"
          @focus="delete errorMessages['eventType']"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-autocomplete
          v-model="eventSubtype"
          outlined
          :label="$t('transactions.events.form.event_subtype.label')"
          :items="historyEventSubTypeData"
          item-value="identifier"
          item-text="label"
          data-cy="eventSubtype"
          :error-messages="errorMessages['eventSubtype']"
          @focus="delete errorMessages['eventSubtype']"
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
      <v-col cols="12" md="6">
        <v-text-field
          v-model="locationLabel"
          outlined
          data-cy="locationLabel"
          :label="$t('transactions.events.form.location_label.label')"
          :error-messages="errorMessages['locationLabel']"
          @focus="delete errorMessages['locationLabel']"
        />
      </v-col>
      <v-col cols="12" md="6">
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
  unref,
  watch
} from '@vue/composition-api';
import { useLocalStorage } from '@vueuse/core';
import dayjs from 'dayjs';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import { setupGeneralBalances } from '@/composables/balances';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import i18n from '@/i18n';
import { convertKeys } from '@/services/axios-tranformers';
import { deserializeApiErrorMessage } from '@/services/converters';
import {
  EthTransactionEvent,
  NewEthTransactionEvent
} from '@/services/history/types';
import {
  historyEventSubTypeData,
  historyEventTypeData
} from '@/store/history/consts';
import {
  EthTransactionEntry,
  EthTransactionEventEntry
} from '@/store/history/types';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { Writeable } from '@/types';
import { TaskType } from '@/types/task-type';
import { HistoryEventSubType, HistoryEventType } from '@/types/transaction';
import { bigNumberifyFromRef, Zero } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

const TransactionEventForm = defineComponent({
  name: 'TransactionEventForm',
  components: { LocationSelector },
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
    const { fetchHistoricPrice } = setupGeneralBalances();

    const lastLocation = useLocalStorage(
      'rotki.ledger_action.location',
      TRADE_LOCATION_EXTERNAL
    );

    const identifier = ref<number | null>(null);
    const eventIdentifier = ref<string>('');
    const sequenceIndex = ref<string>('');
    const datetime = ref<string>('');
    const location = ref<string>('');
    const eventType = ref<string | null>();
    const eventSubtype = ref<string | null>();
    const asset = ref<string>('');
    const amount = ref<string>('');
    const usdValue = ref<string>('');
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

    const usdValueRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('transactions.events.form.usd_value.validation.non_empty')
          .toString()
    ];

    const sequenceIndexRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('transactions.events.form.sequence_index.validation.non_empty')
          .toString()
    ];

    const fetching = computed<boolean>(() => {
      return isTaskRunning(TaskType.FETCH_HISTORIC_PRICE).value;
    });

    const reset = () => {
      identifier.value = null;
      eventIdentifier.value = unref(transaction)?.txHash || '';
      sequenceIndex.value = '0';
      datetime.value = convertFromTimestamp(
        unref(transaction)?.timestamp || dayjs().unix(),
        true
      );
      location.value = '';
      eventType.value = null;
      eventSubtype.value = null;
      asset.value = '';
      amount.value = '0';
      usdValue.value = '0';
      location.value = unref(lastLocation);
      notes.value = '';
      counterparty.value = '';
      rate.value = '';
      errorMessages.value = {};
    };

    const setEditMode = () => {
      if (!unref(edit)) {
        reset();
        return;
      }

      const event: EthTransactionEvent = unref(edit);

      identifier.value = event.identifier ?? null;
      eventIdentifier.value = event.eventIdentifier;
      sequenceIndex.value = event.sequenceIndex?.toString() ?? '';
      datetime.value = convertFromTimestamp(event.timestamp, true);
      location.value = event.location;
      eventType.value = event.eventType;
      eventSubtype.value = event.eventSubtype;
      asset.value = event.asset;
      amount.value = event.balance?.amount?.toString() ?? '';
      usdValue.value = event.balance?.usdValue?.toString() ?? '';
      locationLabel.value = event.locationLabel ?? '';
      notes.value = event.notes ?? '';
      counterparty.value = event.counterparty ?? '';

      fetchPrice();
    };

    const save = async (): Promise<boolean> => {
      const numericAmount = bigNumberifyFromRef(amount).value;
      const numericUsdValue = bigNumberifyFromRef(usdValue).value;

      const transactionEventPayload: Writeable<NewEthTransactionEvent> = {
        eventIdentifier: unref(eventIdentifier),
        sequenceIndex: unref(sequenceIndex) || '0',
        timestamp: convertToTimestamp(unref(datetime)),
        location: unref(location),
        eventType: unref(eventType) as HistoryEventType,
        eventSubtype: unref(eventSubtype) as HistoryEventSubType,
        asset: unref(asset),
        balance: {
          amount: numericAmount.isNaN() ? Zero : numericAmount,
          usdValue: numericUsdValue.isNaN() ? Zero : numericUsdValue
        },
        locationLabel: unref(locationLabel) ? unref(locationLabel) : undefined,
        notes: unref(notes) ? unref(notes) : undefined,
        counterparty: unref(counterparty) ? unref(counterparty) : undefined
      };

      const result = !unref(identifier)
        ? await saveData(transactionEventPayload)
        : await saveData({
            ...transactionEventPayload,
            identifier: unref(identifier)!
          });

      if (result.success) {
        reset();
        return true;
      }

      if (result.message) {
        errorMessages.value = convertKeys(
          deserializeApiErrorMessage(result.message) ?? {},
          true,
          false
        );
      }

      return false;
    };

    const updateUsdValue = () => {
      if (unref(amount) && unref(rate)) {
        usdValue.value = new BigNumber(unref(amount))
          .multipliedBy(new BigNumber(unref(rate)))
          .toString();
      }
    };

    const fetchPrice = async () => {
      if (
        (unref(usdValue) && unref(edit)) ||
        !unref(datetime) ||
        !unref(asset)
      ) {
        return;
      }

      const timestamp = convertToTimestamp(unref(datetime));
      const fromAsset = unref(asset);
      const toAsset = 'USD';

      const rateFromHistoricPrice = await fetchHistoricPrice({
        timestamp,
        fromAsset,
        toAsset
      });

      if (rateFromHistoricPrice.gt(0)) {
        rate.value = rateFromHistoricPrice.toString();
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
      eventIdentifier.value = transaction?.txHash || '';
    });

    watch(location, (location: string) => {
      if (location) {
        lastLocation.value = location;
      }
    });

    onMounted(() => {
      setEditMode();
    });

    return {
      historyEventTypeData,
      historyEventSubTypeData,
      input,
      sequenceIndex,
      datetime,
      location,
      eventType,
      eventSubtype,
      asset,
      amount,
      usdValue,
      locationLabel,
      notes,
      counterparty,
      errorMessages,
      locationRules,
      assetRules,
      amountRules,
      usdValueRules,
      sequenceIndexRules,
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

<style scoped lang="scss">
.transaction-event-form {
  &__amount-wrapper {
    ::v-deep {
      .v-input {
        input {
          height: 60px;
          max-height: 60px !important;
        }
      }

      .v-select {
        &__selections {
          padding: 0 !important;
        }
      }
    }
  }
}
</style>
