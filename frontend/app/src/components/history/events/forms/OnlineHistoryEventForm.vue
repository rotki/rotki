<script setup lang="ts">
import type { EventData, NewOnlineHistoryEventPayload, OnlineHistoryEvent } from '@/types/history/events';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';
import HistoryEventTypeForm from '@/components/history/events/forms/HistoryEventTypeForm.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { useSessionSettingsStore } from '@/store/settings/session';
import { DateFormat } from '@/types/date-format';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { toMessages } from '@/utils/validation';
import { HistoryEventEntryType, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = withDefaults(defineProps<{
  data?: EventData<OnlineHistoryEvent>;
}>(), {
  data: undefined,
});

const { t } = useI18n();

const { data } = toRefs(props);

const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);

const assetPriceForm = ref<InstanceType<typeof HistoryEventAssetPriceForm>>();

const eventIdentifier = ref<string>('');
const sequenceIndex = ref<string>('');
const datetime = ref<string>('');
const location = ref<string>('');
const eventType = ref<string>('');
const eventSubtype = ref<string>('none');
const asset = ref<string>('');
const amount = ref<string>('');
const locationLabel = ref<string>('');
const notes = ref<string>('');

const errorMessages = ref<Record<string, string[]>>({});

const externalServerValidation = () => true;

const rules = {
  amount: {
    required: helpers.withMessage(t('transactions.events.form.amount.validation.non_empty'), required),
  },
  asset: {
    required: helpers.withMessage(t('transactions.events.form.asset.validation.non_empty'), required),
  },
  eventIdentifier: {
    required: helpers.withMessage(t('transactions.events.form.event_identifier.validation.non_empty'), required),
  },
  eventSubtype: {
    required: helpers.withMessage(t('transactions.events.form.event_subtype.validation.non_empty'), required),
  },
  eventType: {
    required: helpers.withMessage(t('transactions.events.form.event_type.validation.non_empty'), required),
  },
  location: {
    required: helpers.withMessage(t('transactions.events.form.location.validation.non_empty'), required),
  },
  locationLabel: { externalServerValidation },
  notes: { externalServerValidation },
  sequenceIndex: {
    required: helpers.withMessage(t('transactions.events.form.sequence_index.validation.non_empty'), required),
  },
  timestamp: { externalServerValidation },
};

const numericAmount = bigNumberifyFromRef(amount);

const { getPayloadNotes, saveHistoryEventHandler } = useHistoryEventsForm();
const { connectedExchanges } = storeToRefs(useSessionSettingsStore());

const states = {
  amount,
  asset,
  eventIdentifier,
  eventSubtype,
  eventType,
  location,
  locationLabel,
  notes,
  sequenceIndex,
  timestamp: datetime,
};

const v$ = useVuelidate(
  rules,
  states,
  {
    $autoDirty: true,
    $externalResults: errorMessages,
  },
);

useFormStateWatcher(states, stateUpdated);

const locationLabelSuggestions = computed(() =>
  get(connectedExchanges)
    .map(item => item.name)
    .filter(item => !!item),
);

function reset() {
  set(sequenceIndex, get(data)?.nextSequenceId || '0');
  set(eventIdentifier, '');
  set(datetime, convertFromTimestamp(dayjs().valueOf(), DateFormat.DateMonthYearHourMinuteSecond, true));
  set(location, get(lastLocation));
  set(locationLabel, '');
  set(eventType, '');
  set(eventSubtype, 'none');
  set(asset, '');
  set(amount, '0');
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
  set(amount, entry.amount.toFixed());
  set(locationLabel, entry.locationLabel ?? '');
  set(notes, entry.notes ?? '');
}

function applyGroupHeaderData(entry: OnlineHistoryEvent) {
  set(sequenceIndex, get(data)?.nextSequenceId || '0');
  set(location, entry.location || get(lastLocation));
  set(locationLabel, entry.locationLabel ?? '');
  set(eventIdentifier, entry.eventIdentifier);
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
}

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const timestamp = convertToTimestamp(get(datetime), DateFormat.DateMonthYearHourMinuteSecond, true);

  const editable = get(data)?.event;
  const usedNotes = getPayloadNotes(get(notes), editable?.notes);

  const payload: NewOnlineHistoryEventPayload = {
    amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
    asset: get(asset),
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventIdentifier: get(eventIdentifier),
    eventSubtype: get(eventSubtype),
    eventType: get(eventType),
    location: get(location),
    locationLabel: get(locationLabel) || null,
    notes: usedNotes ? usedNotes.trim() : undefined,
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp,
  };

  return await saveHistoryEventHandler(
    editable ? { ...payload, identifier: editable.identifier } : payload,
    assetPriceForm,
    errorMessages,
    reset,
  );
}

function checkPropsData() {
  const formData = get(data);
  const editable = formData?.event;
  if (editable) {
    applyEditableData(editable);
    return;
  }
  const group = formData?.group;
  if (group) {
    applyGroupHeaderData(group);
    return;
  }
  reset();
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

watch(location, (location: string) => {
  if (location)
    set(lastLocation, location);
});

watch(data, checkPropsData);

onMounted(() => {
  checkPropsData();
});

defineExpose({
  save,
});
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
        :disabled="!!(data?.event || data?.group)"
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
      :disabled="!!(data?.event || data?.group)"
      data-cy="eventIdentifier"
      :label="t('transactions.events.form.event_identifier.label')"
      :error-messages="toMessages(v$.eventIdentifier)"
      @blur="v$.eventIdentifier.$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventTypeForm
      v-model:event-type="eventType"
      v-model:event-subtype="eventSubtype"
      :location="location"
      :v$="v$"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      ref="assetPriceForm"
      v-model:asset="asset"
      v-model:amount="amount"
      :v$="v$"
      :datetime="datetime"
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
      prepend-icon="lu-sticky-note"
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
