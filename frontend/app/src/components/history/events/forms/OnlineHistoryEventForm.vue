<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import dayjs from 'dayjs';
import { helpers, required } from '@vuelidate/validators';
import {
  type NewOnlineHistoryEventPayload,
  type OnlineHistoryEvent
} from '@/types/history/events';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { type Writeable } from '@/types';
import { type ActionDataEntry } from '@/types/action';
import { toMessages } from '@/utils/validation';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';

const props = withDefaults(
  defineProps<{
    editableItem: OnlineHistoryEvent | null;
    nextSequence?: string | null;
    groupHeader: OnlineHistoryEvent | null;
  }>(),
  {
    nextSequence: ''
  }
);

const { t } = useI18n();

const { editableItem, groupHeader, nextSequence } = toRefs(props);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const {
  getEventTypeData,
  historyEventTypesData,
  historyEventSubTypesData,
  historyEventTypeGlobalMapping,
  historyEventTypeExchangeMapping
} = useHistoryEventMappings();

const lastLocation = useLocalStorage(
  'rotki.history_event.location',
  TRADE_LOCATION_EXTERNAL
);

const assetPriceForm: Ref<InstanceType<
  typeof HistoryEventAssetPriceForm
> | null> = ref(null);

const eventIdentifier: Ref<string> = ref('');
const sequenceIndex: Ref<string> = ref('');
const datetime: Ref<string> = ref('');
const location: Ref<string> = ref('');
const eventType: Ref<string> = ref('');
const eventSubtype: Ref<string> = ref('');
const asset: Ref<string> = ref('');
const amount: Ref<string> = ref('');
const usdValue: Ref<string> = ref('');
const locationLabel: Ref<string> = ref('');
const notes: Ref<string> = ref('');

const transactionEventType: Ref<string | null> = ref('');

const errorMessages = ref<Record<string, string[]>>({});

const externalServerValidation = () => true;

const rules = {
  timestamp: { externalServerValidation },
  locationLabel: { externalServerValidation },
  notes: { externalServerValidation },
  eventIdentifier: {
    required: helpers.withMessage(
      t(
        'transactions.events.form.event_identifier.validation.non_empty'
      ).toString(),
      required
    )
  },
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

const { setValidation, setSubmitFunc } = useHistoryEventsForm();

const v$ = setValidation(
  rules,
  {
    timestamp: datetime,
    locationLabel,
    notes,
    eventIdentifier,
    location,
    asset,
    amount,
    usdValue,
    sequenceIndex,
    eventType,
    eventSubtype
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages
  }
);

const reset = () => {
  set(sequenceIndex, get(nextSequence) ?? '0');
  set(eventIdentifier, '');
  set(datetime, convertFromTimestamp(dayjs().unix(), true));
  set(location, get(lastLocation));
  set(locationLabel, '');
  set(eventType, '');
  set(eventSubtype, '');
  set(asset, '');
  set(amount, '0');
  set(usdValue, '0');
  set(notes, '');
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
};

const applyEditableData = async (entry: OnlineHistoryEvent) => {
  set(sequenceIndex, entry.sequenceIndex?.toString() ?? '');
  set(eventIdentifier, entry.eventIdentifier);
  set(datetime, convertFromTimestamp(entry.timestamp, true));
  set(location, entry.location);
  set(eventType, entry.eventType);
  set(eventSubtype, entry.eventSubtype || 'none');
  set(asset, entry.asset);
  set(amount, entry.balance.amount.toFixed());
  set(usdValue, entry.balance.usdValue.toFixed());
  set(locationLabel, entry.locationLabel ?? '');
  set(notes, entry.notes ?? '');
};

const applyGroupHeaderData = async (entry: OnlineHistoryEvent) => {
  set(sequenceIndex, get(nextSequence) ?? '0');
  set(location, entry.location || get(lastLocation));
  set(locationLabel, entry.locationLabel ?? '');
  set(eventIdentifier, entry.eventIdentifier);
  set(datetime, convertFromTimestamp(entry.timestamp, true));
};

const { setMessage } = useMessageStore();

const { editHistoryEvent, addHistoryEvent } = useHistoryTransactions();

const save = async (): Promise<boolean> => {
  const timestamp = convertToTimestamp(get(datetime));
  const assetVal = get(asset);

  const payload: Writeable<NewOnlineHistoryEventPayload> = {
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventIdentifier: get(eventIdentifier),
    sequenceIndex: get(sequenceIndex) || '0',
    // Change this
    timestamp: timestamp * 1000,
    eventType: get(eventType),
    eventSubtype: get(eventSubtype),
    asset: assetVal,
    balance: {
      amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
      usdValue: get(numericUsdValue).isNaN() ? Zero : get(numericUsdValue)
    },
    location: get(location),
    locationLabel: get(locationLabel) || null,
    notes: get(notes) || undefined
  };

  const submitPriceResult = await get(assetPriceForm)!.submitPrice(payload);

  if (!submitPriceResult.success) {
    set(errorMessages, submitPriceResult.message);
    return false;
  }

  const edit = get(editableItem);
  const result = !edit
    ? await addHistoryEvent(payload)
    : await editHistoryEvent({
        ...payload,
        identifier: edit.identifier
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

const numericAmount = bigNumberifyFromRef(amount);
const numericUsdValue = bigNumberifyFromRef(usdValue);

watch(location, (location: string) => {
  if (location) {
    set(lastLocation, location);
  }
});

watch(
  [eventType, eventSubtype, location],
  ([eventType, eventSubtype, location]) => {
    const typeData = get(
      getEventTypeData(
        {
          eventType,
          eventSubtype,
          location,
          entryType: HistoryEventEntryType.HISTORY_EVENT
        },
        false
      )
    );
    set(transactionEventType, typeData.label);
  }
);

const checkPropsData = () => {
  const editable = get(editableItem);
  if (editable) {
    applyEditableData(editable);
    return;
  }
  const group = get(groupHeader);
  if (group) {
    applyGroupHeaderData(group);
    return;
  }
  reset();
};

watch([groupHeader, editableItem], checkPropsData);
onMounted(() => {
  checkPropsData();
});

const historyEventSubTypeFilteredData: ComputedRef<ActionDataEntry[]> =
  computed(() => {
    const eventTypeVal = get(eventType);
    const allData = get(historyEventSubTypesData);
    const globalMapping = get(historyEventTypeGlobalMapping);
    const exchangeMapping = get(historyEventTypeExchangeMapping);
    const locationVal = get(location);

    if (!eventTypeVal) {
      return allData;
    }

    let globalMappingKeys: string[] = [];

    const globalMappingFound = globalMapping[eventTypeVal];
    if (globalMappingFound) {
      globalMappingKeys = Object.keys(globalMappingFound);
    }

    let exchangeMappingKeys: string[] = [];

    if (locationVal) {
      const exchangeMappingObj = exchangeMapping?.[locationVal]?.[eventTypeVal];
      if (exchangeMappingObj) {
        exchangeMappingKeys = Object.keys(exchangeMappingObj);
      }
    }

    return allData.filter(
      (data: ActionDataEntry) =>
        globalMappingKeys.includes(data.identifier) ||
        exchangeMappingKeys.includes(data.identifier)
    );
  });
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 gap-4">
      <DateTimePicker
        v-model="datetime"
        outlined
        :label="t('transactions.events.form.datetime.label')"
        persistent-hint
        limit-now
        milliseconds
        data-cy="datetime"
        :hint="t('transactions.events.form.datetime.hint')"
        :error-messages="toMessages(v$.timestamp)"
        @blur="v$.timestamp.$touch()"
      />
      <LocationSelector
        v-model="location"
        required
        outlined
        :disabled="!!(editableItem || groupHeader)"
        data-cy="location"
        :label="t('common.location')"
        :error-messages="toMessages(v$.location)"
        @blur="v$.location.$touch()"
      />
    </div>

    <VTextField
      v-model="eventIdentifier"
      outlined
      :disabled="!!(editableItem || groupHeader)"
      data-cy="eventIdentifier"
      :label="t('transactions.events.form.event_identifier.label')"
      :error-messages="toMessages(v$.eventIdentifier)"
      @blur="v$.eventIdentifier.$touch()"
    />

    <div class="border-t mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      ref="assetPriceForm"
      :v$="v$"
      :datetime="datetime"
      :asset.sync="asset"
      :amount.sync="amount"
      :usd-value.sync="usdValue"
    />

    <div class="border-t my-10" />

    <div class="grid md:grid-cols-3 gap-4">
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
      <VTextField
        v-model="transactionEventType"
        outlined
        required
        disabled
        :label="t('transactions.events.form.transaction_event_type.label')"
      />
    </div>

    <div class="border-t mb-6 mt-2" />

    <div class="grid md:grid-cols-2 gap-4">
      <VTextField
        v-model="locationLabel"
        :disabled="!!(editableItem || groupHeader)"
        outlined
        data-cy="locationLabel"
        :label="t('transactions.events.form.location_label.label')"
        :error-messages="toMessages(v$.locationLabel)"
        @blur="v$.locationLabel.$touch()"
      />
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
    </div>

    <div class="border-t mb-6 mt-2" />

    <VTextarea
      v-model.trim="notes"
      prepend-inner-icon="mdi-text-box-outline"
      persistent-hint
      outlined
      data-cy="notes"
      :label="t('transactions.events.form.notes.label')"
      :hint="t('transactions.events.form.notes.hint')"
      :error-messages="toMessages(v$.notes)"
      @blur="v$.notes.$touch()"
    />
  </div>
</template>
