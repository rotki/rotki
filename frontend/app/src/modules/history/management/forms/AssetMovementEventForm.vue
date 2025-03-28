<script setup lang="ts">
import type { DependentEventData } from '@/modules/history/management/forms/form-types';
import type { AssetMovementEvent, NewAssetMovementEventPayload } from '@/types/history/events';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { refIsTruthy } from '@/composables/ref';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useSessionSettingsStore } from '@/store/settings/session';
import { DateFormat } from '@/types/date-format';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { toMessages } from '@/utils/validation';
import { HistoryEventEntryType, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { isEqual } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';

interface AssetMovementEventFormProps {
  data: DependentEventData<AssetMovementEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<AssetMovementEventFormProps>();

const { t } = useI18n();

const { data } = toRefs(props);

const historyEventTypesData = [{
  identifier: 'deposit',
  label: t('backend_mappings.events.history_event_type.deposit'),
}, {
  identifier: 'withdrawal',
  label: t('backend_mappings.events.history_event_type.withdrawal'),
}];

const assetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('assetPriceForm');

const eventIdentifier = ref<string>('');
const datetime = ref<string>('');
const location = ref<string>('');
const locationLabel = ref<string>('');
const eventType = ref<string>('');
const asset = ref<string>('');
const amount = ref<string>('');
const notes = ref<string>('');
const hasFee = ref<boolean>(false);
const fee = ref<string>('');
const feeAsset = ref<string>('');
const uniqueId = ref<string>('');

const errorMessages = ref<Record<string, string[]>>({});

const externalServerValidation = () => true;

const rules = {
  amount: {
    required: helpers.withMessage(t('transactions.events.form.amount.validation.non_empty'), required),
  },
  asset: {
    required: helpers.withMessage(t('transactions.events.form.asset.validation.non_empty'), required),
  },
  eventIdentifier: { externalServerValidation },
  eventType: {
    required: helpers.withMessage(t('transactions.events.form.event_type.validation.non_empty'), required),
  },
  fee: {
    required: helpers.withMessage(
      t('transactions.events.form.fee.validation.non_empty'),
      requiredIf(logicAnd(hasFee, refIsTruthy(feeAsset))),
    ),
  },
  feeAsset: {
    required: helpers.withMessage(
      t('transactions.events.form.fee_asset.validation.non_empty'),
      requiredIf(logicAnd(hasFee, refIsTruthy(fee))),
    ),
  },
  location: {
    required: helpers.withMessage(t('transactions.events.form.location.validation.non_empty'), required),
  },
  locationLabel: { externalServerValidation },
  notes: { externalServerValidation },
  timestamp: { externalServerValidation },
  uniqueId: { externalServerValidation },
};

const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
const { saveHistoryEventHandler } = useHistoryEventsForm();

const states = {
  amount,
  asset,
  eventIdentifier,
  eventType,
  fee,
  feeAsset,
  location,
  locationLabel,
  notes,
  timestamp: datetime,
  uniqueId,
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

const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);
const numericAmount = bigNumberifyFromRef(amount);
const locationLabelSuggestions = computed<string[]>(() => {
  const suggestions: string[] = [];

  for (const { location: connectedLocation, name } of get(connectedExchanges)) {
    if (connectedLocation !== get(location) || !name) {
      continue;
    }
    suggestions.push(name);
  }
  return suggestions;
});

function reset() {
  set(eventIdentifier, '');
  set(datetime, convertFromTimestamp(dayjs().valueOf(), DateFormat.DateMonthYearHourMinuteSecond, true));
  set(location, get(lastLocation));
  set(locationLabel, '');
  set(eventType, 'deposit');
  set(asset, '');
  set(amount, '0');
  set(notes, '');
  set(errorMessages, {});
  set(uniqueId, '');

  get(assetPriceForm)?.reset();
}

function applyEditableData(entry: AssetMovementEvent, feeEvent?: AssetMovementEvent) {
  set(eventIdentifier, entry.eventIdentifier);
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
  set(location, entry.location);
  set(locationLabel, entry.locationLabel ?? '');
  set(eventType, entry.eventType);
  set(asset, entry.asset ?? '');
  set(amount, entry.amount.toFixed());
  set(notes, entry.notes ?? '');

  if (feeEvent) {
    set(fee, feeEvent.amount.toFixed());
    set(feeAsset, feeEvent.asset ?? '');
    set(hasFee, true);
  }
  else {
    set(hasFee, false);
  }

  if (entry.extraData?.reference) {
    set(uniqueId, entry.extraData.reference);
  }
}

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const timestamp = convertToTimestamp(get(datetime), DateFormat.DateMonthYearHourMinuteSecond, true);

  const eventData = get(data);
  const editable = eventData.type === 'edit-group' ? eventData.eventsInGroup[0] : undefined;

  let payload: NewAssetMovementEventPayload = {
    amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
    asset: get(asset),
    entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    eventIdentifier: get(eventIdentifier),
    eventType: get(eventType),
    fee: null,
    feeAsset: null,
    location: get(location),
    locationLabel: get(locationLabel),
    notes: get(notes),
    timestamp,
    uniqueId: get(uniqueId),
  };

  if (get(hasFee)) {
    payload = {
      ...payload,
      fee: get(fee) || null,
      feeAsset: get(feeAsset) || null,
    };
  }

  return await saveHistoryEventHandler(
    editable ? { ...payload, identifier: editable.identifier } : payload,
    assetPriceForm,
    errorMessages,
    reset,
  );
}

function checkPropsData() {
  const formData = get(data);

  if (formData.type === 'edit-group') {
    const editable = formData.eventsInGroup[0];
    const feeEvent = formData.eventsInGroup.find(event => event.eventSubtype === 'fee');
    applyEditableData(editable, feeEvent);
    return;
  }
  reset();
}

watchImmediate(data, (data, oldData) => {
  if (isEqual(data, oldData)) {
    return;
  }
  checkPropsData();
});

watch(location, (location: string) => {
  if (location)
    set(lastLocation, location);
});

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
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
        :disabled="data.type === 'edit-group'"
        data-cy="location"
        :label="t('common.location')"
        :error-messages="toMessages(v$.location)"
        @blur="v$.location.$touch()"
      />
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
    </div>

    <RuiAutoComplete
      v-model="eventType"
      variant="outlined"
      :label="t('transactions.events.form.event_type.label')"
      :options="historyEventTypesData"
      key-attr="identifier"
      text-attr="label"
      data-cy="eventType"
      auto-select-first
      :error-messages="toMessages(v$.eventType)"
      @blur="v$.eventType.$touch()"
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

    <RuiTextField
      v-model="uniqueId"
      variant="outlined"
      color="primary"
      :label="t('transactions.events.form.unique_id.label')"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiCheckbox
      v-model="hasFee"
      label="Has Fee"
      color="primary"
    />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="fee"
        :disabled="!hasFee"
        clearable
        variant="outlined"
        data-cy="amount"
        :label="t('common.fee')"
        :error-messages="toMessages(v$.fee)"
      />
      <AssetSelect
        v-model="feeAsset"
        :disabled="!hasFee"
        outlined
        clearable
        data-cy="feeAsset"
        :label="t('transactions.events.form.fee_asset.label')"
        :error-messages="toMessages(v$.feeAsset)"
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

    <RuiDivider class="mb-2 mt-6" />

    <RuiAccordions>
      <RuiAccordion
        data-cy="asset-movement-event-form__advance"
        header-class="py-4"
        eager
      >
        <template #header>
          {{ t('transactions.events.form.advanced') }}
        </template>
        <div class="py-2">
          <RuiTextField
            v-model="eventIdentifier"
            variant="outlined"
            color="primary"
            data-cy="eventIdentifier"
            :label="t('transactions.events.form.event_identifier.label')"
            :error-messages="toMessages(v$.eventIdentifier)"
            @blur="v$.eventIdentifier.$touch()"
          />
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>
