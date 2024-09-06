<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common';
import dayjs from 'dayjs';
import { helpers, required } from '@vuelidate/validators';
import { isEmpty } from 'lodash-es';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { toMessages } from '@/utils/validation';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';
import { DateFormat } from '@/types/date-format';
import type { NewOnlineHistoryEventPayload, OnlineHistoryEvent } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    editableItem?: OnlineHistoryEvent;
    nextSequence?: string;
    groupHeader?: OnlineHistoryEvent;
  }>(),
  {
    editableItem: undefined,
    nextSequence: '',
    groupHeader: undefined,
  },
);

const { t } = useI18n();

const { editableItem, groupHeader, nextSequence } = toRefs(props);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);

const assetPriceForm = ref<InstanceType<typeof HistoryEventAssetPriceForm>>();

const eventIdentifier = ref<string>('');
const sequenceIndex = ref<string>('');
const datetime = ref<string>('');
const location = ref<string>('');
const eventType = ref<string>('');
const eventSubtype = ref<string>('');
const asset = ref<string>('');
const amount = ref<string>('');
const usdValue = ref<string>('');
const locationLabel = ref<string>('');
const notes = ref<string>('');

const errorMessages = ref<Record<string, string[]>>({});

const externalServerValidation = () => true;

const rules = {
  timestamp: { externalServerValidation },
  locationLabel: { externalServerValidation },
  notes: { externalServerValidation },
  eventIdentifier: {
    required: helpers.withMessage(t('transactions.events.form.event_identifier.validation.non_empty'), required),
  },
  location: {
    required: helpers.withMessage(t('transactions.events.form.location.validation.non_empty'), required),
  },
  asset: {
    required: helpers.withMessage(t('transactions.events.form.asset.validation.non_empty'), required),
  },
  amount: {
    required: helpers.withMessage(t('transactions.events.form.amount.validation.non_empty'), required),
  },
  usdValue: {
    required: helpers.withMessage(
      t('transactions.events.form.fiat_value.validation.non_empty', {
        currency: get(currencySymbol),
      }),
      required,
    ),
  },
  sequenceIndex: {
    required: helpers.withMessage(t('transactions.events.form.sequence_index.validation.non_empty'), required),
  },
  eventType: {
    required: helpers.withMessage(t('transactions.events.form.event_type.validation.non_empty'), required),
  },
  eventSubtype: {
    required: helpers.withMessage(t('transactions.events.form.event_subtype.validation.non_empty'), required),
  },
};

const numericAmount = bigNumberifyFromRef(amount);
const numericUsdValue = bigNumberifyFromRef(usdValue);

const { setValidation, setSubmitFunc, saveHistoryEventHandler, getPayloadNotes } = useHistoryEventsForm();

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
    eventSubtype,
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages,
  },
);

function reset() {
  set(sequenceIndex, get(nextSequence) || '0');
  set(eventIdentifier, '');
  set(datetime, convertFromTimestamp(dayjs().valueOf(), DateFormat.DateMonthYearHourMinuteSecond, true));
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
}

function applyEditableData(entry: OnlineHistoryEvent) {
  set(sequenceIndex, entry.sequenceIndex?.toString() ?? '');
  set(eventIdentifier, entry.eventIdentifier);
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
  set(location, entry.location);
  set(eventType, entry.eventType);
  set(eventSubtype, entry.eventSubtype || 'none');
  set(asset, entry.asset);
  set(amount, entry.balance.amount.toFixed());
  set(usdValue, entry.balance.usdValue.toFixed());
  set(locationLabel, entry.locationLabel ?? '');
  set(notes, entry.notes ?? '');
}

function applyGroupHeaderData(entry: OnlineHistoryEvent) {
  set(sequenceIndex, get(nextSequence) || '0');
  set(location, entry.location || get(lastLocation));
  set(locationLabel, entry.locationLabel ?? '');
  set(eventIdentifier, entry.eventIdentifier);
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
  set(usdValue, '0');
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

async function save(): Promise<boolean> {
  const timestamp = convertToTimestamp(get(datetime), DateFormat.DateMonthYearHourMinuteSecond, true);

  const editable = get(editableItem);
  const usedNotes = getPayloadNotes(get(notes), editable?.notes);

  const payload: NewOnlineHistoryEventPayload = {
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventIdentifier: get(eventIdentifier),
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp,
    eventType: get(eventType),
    eventSubtype: get(eventSubtype),
    asset: get(asset),
    balance: {
      amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
      usdValue: get(numericUsdValue).isNaN() ? Zero : get(numericUsdValue),
    },
    location: get(location),
    locationLabel: get(locationLabel) || null,
    notes: usedNotes ? usedNotes.trim() : undefined,
  };

  return await saveHistoryEventHandler(
    editable ? { ...payload, identifier: editable.identifier } : payload,
    assetPriceForm,
    errorMessages,
    reset,
  );
}

setSubmitFunc(save);

watch(location, (location: string) => {
  if (location)
    set(lastLocation, location);
});

function checkPropsData() {
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
}

watch([groupHeader, editableItem], checkPropsData);
onMounted(() => {
  checkPropsData();
});

const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
const locationLabelSuggestions = computed(() =>
  get(connectedExchanges)
    .map(item => item.name)
    .filter(item => !!item),
);
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 gap-4 mb-4">
      <DateTimePicker
        v-model="datetime"
        :label="t('common.datetime')"
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
        :disabled="!!(editableItem || groupHeader)"
        data-cy="location"
        :label="t('common.location')"
        :error-messages="toMessages(v$.location)"
        @blur="v$.location.$touch()"
      />
    </div>

    <RuiTextField
      v-model="eventIdentifier"
      variant="outlined"
      color="primary"
      :disabled="!!(editableItem || groupHeader)"
      data-cy="eventIdentifier"
      :label="t('transactions.events.form.event_identifier.label')"
      :error-messages="toMessages(v$.eventIdentifier)"
      @blur="v$.eventIdentifier.$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      ref="assetPriceForm"
      v-model:asset="asset"
      v-model:amount="amount"
      v-model:usd-value="usdValue"
      :v$="v$"
      :datetime="datetime"
    />

    <RuiDivider class="my-10" />

    <HistoryEventTypeForm
      v-model:event-type="eventType"
      v-model:event-subtype="eventSubtype"
      :location="location"
      :v$="v$"
    />

    <RuiDivider class="mb-6 mt-2" />

    <div class="grid md:grid-cols-2 gap-4">
      <AutoCompleteWithSearchSync
        v-model="locationLabel"
        :items="locationLabelSuggestions"
        clearable
        data-cy="locationLabel"
        :label="t('transactions.events.form.location_label.label')"
        :error-messages="toMessages(v$.locationLabel)"
        auto-select-first
        @blur="v$.locationLabel.$touch()"
      />
      <AmountInput
        v-model="sequenceIndex"
        variant="outlined"
        integer
        data-cy="sequenceIndex"
        :label="t('transactions.events.form.sequence_index.label')"
        :error-messages="toMessages(v$.sequenceIndex)"
        @blur="v$.sequenceIndex.$touch()"
      />
    </div>

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextArea
      v-model="notes"
      prepend-icon="sticky-note-line"
      data-cy="notes"
      variant="outlined"
      color="primary"
      max-rows="5"
      min-rows="3"
      auto-grow
      :label="t('common.notes')"
      :hint="t('transactions.events.form.notes.hint')"
      :error-messages="toMessages(v$.notes)"
      @blur="v$.notes.$touch()"
    />
  </div>
</template>
