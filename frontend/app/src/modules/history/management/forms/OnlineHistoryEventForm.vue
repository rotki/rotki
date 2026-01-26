<script setup lang="ts">
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import type { NewOnlineHistoryEventPayload, OnlineHistoryEvent } from '@/types/history/events/schemas';
import { HistoryEventEntryType, Zero } from '@rotki/common';
import { generateUUID } from '@shared/utils';
import dayjs from 'dayjs';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { toMessages, useEventFormBase } from '@/modules/history/management/forms/composables/use-event-form-base';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import { useSessionSettingsStore } from '@/store/settings/session';
import { bigNumberifyFromRef } from '@/utils/bignumbers';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<{ data: StandaloneEventData<OnlineHistoryEvent> }>();

const { t } = useI18n({ useScope: 'global' });

const { data } = toRefs(props);

const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);

const assetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('assetPriceForm');

const groupIdentifier = ref<string>('');
const hasActualGroupIdentifier = ref<boolean>(false);
const sequenceIndex = ref<string>('');
const timestamp = ref<number>(0);
const location = ref<string>('');
const eventType = ref<string>('');
const eventSubtype = ref<string>('none');
const asset = ref<string>('');
const amount = ref<string>('');
const locationLabel = ref<string>('');
const notes = ref<string>('');

const errorMessages = ref<Record<string, string[]>>({});

const states = {
  amount,
  asset,
  eventSubtype,
  eventType,
  groupIdentifier,
  location,
  locationLabel,
  notes,
  sequenceIndex,
  timestamp,
};

const {
  v$,
  captureEditModeStateFromRefs,
  shouldSkipSaveFromRefs,
} = useEventFormBase({
  rules: commonRules => ({
    amount: commonRules.createRequiredAmountRule(),
    asset: commonRules.createRequiredAssetRule(),
    eventSubtype: commonRules.createRequiredEventSubtypeRule(),
    eventType: commonRules.createRequiredEventTypeRule(),
    groupIdentifier: commonRules.createRequiredGroupIdentifierRule(() => get(data).type === 'edit'),
    location: commonRules.createRequiredLocationRule(),
    locationLabel: commonRules.createExternalValidationRule(),
    notes: commonRules.createExternalValidationRule(),
    sequenceIndex: commonRules.createRequiredSequenceIndexRule(),
    timestamp: commonRules.createExternalValidationRule(),
  }),
  states,
  errorMessages,
  stateUpdated,
});

const numericAmount = bigNumberifyFromRef(amount);

const { saveHistoryEventHandler } = useHistoryEventsForm();
const { connectedExchanges } = storeToRefs(useSessionSettingsStore());

const locationLabelSuggestions = computed(() =>
  get(connectedExchanges)
    .map(item => item.name)
    .filter(item => !!item),
);

function reset() {
  set(sequenceIndex, get(data)?.nextSequenceId || '0');
  set(groupIdentifier, '');
  set(hasActualGroupIdentifier, false);
  set(timestamp, dayjs().valueOf());
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
  const hasActual = !!entry.actualGroupIdentifier;
  set(hasActualGroupIdentifier, hasActual);
  set(groupIdentifier, hasActual ? entry.actualGroupIdentifier! : entry.groupIdentifier);
  set(timestamp, entry.timestamp);
  set(location, entry.location);
  set(eventType, entry.eventType);
  set(eventSubtype, entry.eventSubtype || 'none');
  set(asset, entry.asset);
  set(amount, entry.amount.toFixed());
  set(locationLabel, entry.locationLabel ?? '');
  set(notes, entry.userNotes ?? '');

  // Capture state snapshot for edit mode comparison
  captureEditModeStateFromRefs(states);
}

function applyGroupHeaderData(entry: OnlineHistoryEvent) {
  set(sequenceIndex, get(data)?.nextSequenceId || '0');
  set(location, entry.location || get(lastLocation));
  set(locationLabel, entry.locationLabel ?? '');
  set(groupIdentifier, entry.groupIdentifier);
  set(timestamp, entry.timestamp);
}

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const eventData = get(data);
  const editable = eventData.type === 'edit' ? eventData.event : undefined;
  const userNotes = get(notes).trim();

  // Generate UUID for eventIdentifier if not present and not in edit mode
  const generatedGroupIdentifier = !editable && !get(groupIdentifier) ? generateUUID() : get(groupIdentifier);

  const payload: NewOnlineHistoryEventPayload = {
    amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
    asset: get(asset),
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventSubtype: get(eventSubtype),
    eventType: get(eventType),
    groupIdentifier: generatedGroupIdentifier,
    location: get(location),
    locationLabel: get(locationLabel) || null,
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp: get(timestamp),
    userNotes: userNotes.length > 0 ? userNotes : undefined,
  };

  return await saveHistoryEventHandler(
    editable ? { ...payload, identifier: editable.identifier } : payload,
    assetPriceForm,
    errorMessages,
    reset,
    shouldSkipSaveFromRefs(!!editable, states),
  );
}

function checkPropsData() {
  const formData = get(data);
  if (formData.type === 'edit') {
    applyEditableData(formData.event);
    return;
  }
  if (formData.type === 'group-add') {
    applyGroupHeaderData(formData.group);
    return;
  }
  reset();
}

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
  v$,
});
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 gap-4 mb-4">
      <DateTimePicker
        v-model="timestamp"
        :label="t('common.datetime')"
        required
        persistent-hint
        max-date="now"
        variant="outlined"
        accuracy="millisecond"
        data-cy="datetime"
        :hint="t('transactions.events.form.datetime.hint')"
        :error-messages="toMessages(v$.timestamp)"
        @blur="v$.timestamp.$touch()"
      />
      <LocationSelector
        v-model="location"
        :disabled="data.type !== 'add'"
        data-cy="location"
        :label="t('common.location')"
        required
        :error-messages="toMessages(v$.location)"
        @blur="v$.location.$touch()"
      />
    </div>

    <RuiTextField
      v-model="groupIdentifier"
      variant="outlined"
      color="primary"
      :disabled="data.type !== 'add' || hasActualGroupIdentifier"
      data-cy="groupIdentifier"
      :label="t('transactions.events.form.event_identifier.label')"
      :required="data.type === 'edit'"
      :error-messages="toMessages(v$.groupIdentifier)"
      @blur="v$.groupIdentifier.$touch()"
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
      :location="location"
      :v$="v$"
      :timestamp="timestamp"
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
        data-cy="sequence-index"
        :label="t('transactions.events.form.sequence_index.label')"
        required
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
