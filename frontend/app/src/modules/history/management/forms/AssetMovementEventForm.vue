<script setup lang="ts">
import type { GroupEventData } from '@/modules/history/management/forms/form-types';
import type { AssetMovementEvent, NewAssetMovementEventPayload } from '@/types/history/events';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { refIsTruthy } from '@/composables/ref';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { useSessionSettingsStore } from '@/store/settings/session';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { toMessages } from '@/utils/validation';
import { HistoryEventEntryType, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { isEqual } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';

interface AssetMovementEventFormProps {
  data: GroupEventData<AssetMovementEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<AssetMovementEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

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
const timestamp = ref<number>(0);
const location = ref<string>('');
const locationLabel = ref<string>('');
const eventType = ref<string>('');
const asset = ref<string>('');
const amount = ref<string>('');
const notes = ref<[string, string] | [string]>(['']);
const hasFee = ref<boolean>(false);
const fee = ref<string>('');
const feeAsset = ref<string>('');
const uniqueId = ref<string>('');

const errorMessages = ref<Record<string, string[]>>({});

const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const rules = {
  amount: commonRules.createRequiredAmountRule(),
  asset: commonRules.createRequiredAssetRule(),
  eventIdentifier: commonRules.createExternalValidationRule(),
  eventType: commonRules.createRequiredEventTypeRule(),
  fee: commonRules.createRequiredFeeRule(requiredIf(logicAnd(hasFee, refIsTruthy(feeAsset)))),
  feeAsset: commonRules.createRequiredFeeAssetRule(requiredIf(logicAnd(hasFee, refIsTruthy(fee)))),
  location: commonRules.createRequiredLocationRule(),
  locationLabel: commonRules.createExternalValidationRule(),
  notes: commonRules.createExternalValidationRule(),
  timestamp: commonRules.createExternalValidationRule(),
  uniqueId: commonRules.createExternalValidationRule(),
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
  timestamp,
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
  set(timestamp, dayjs().valueOf());
  set(location, get(lastLocation));
  set(locationLabel, '');
  set(eventType, 'deposit');
  set(asset, '');
  set(amount, '0');
  set(notes, ['']);
  set(errorMessages, {});
  set(uniqueId, '');

  get(assetPriceForm)?.reset();
}

function applyEditableData(entry: AssetMovementEvent, feeEvent?: AssetMovementEvent) {
  const eventNotes = entry.userNotes ?? '';

  set(eventIdentifier, entry.eventIdentifier);
  set(timestamp, entry.timestamp);
  set(location, entry.location);
  set(locationLabel, entry.locationLabel ?? '');
  set(eventType, entry.eventType);
  set(asset, entry.asset ?? '');
  set(amount, entry.amount.toFixed());

  if (feeEvent) {
    set(fee, feeEvent.amount.toFixed());
    set(feeAsset, feeEvent.asset ?? '');
    set(hasFee, true);
    set(notes, [eventNotes, feeEvent.userNotes ?? '']);
  }
  else {
    set(hasFee, false);
    set(notes, [eventNotes]);
  }

  if (entry.extraData?.reference) {
    set(uniqueId, entry.extraData.reference);
  }
}

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

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
    timestamp: get(timestamp),
    uniqueId: get(uniqueId),
    userNotes: get(notes),
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

watch(hasFee, (hasFee: boolean) => {
  if (!hasFee) {
    set(fee, '');
    set(feeAsset, '');
    set(notes, [get(notes)[0]]);
  }
  else {
    set(notes, [get(notes)[0], '']);
  }
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
      <RuiDateTimePicker
        v-model="timestamp"
        :label="t('common.datetime')"
        persistent-hint
        max-date="now"
        color="primary"
        variant="outlined"
        type="epoch-ms"
        accuracy="millisecond"
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
      :location="location"
      :v$="v$"
      :timestamp="timestamp"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextField
      v-model="uniqueId"
      variant="outlined"
      data-cy="unique-id"
      color="primary"
      :label="t('transactions.events.form.unique_id.label')"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiCheckbox
      v-model="hasFee"
      data-cy="has-fee"
      label="Has Fee"
      color="primary"
    />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="fee"
        :disabled="!hasFee"
        clearable
        variant="outlined"
        data-cy="fee-amount"
        :label="t('common.fee')"
        :error-messages="toMessages(v$.fee)"
      />
      <AssetSelect
        v-model="feeAsset"
        :disabled="!hasFee"
        outlined
        clearable
        data-cy="fee-asset"
        :label="t('transactions.events.form.fee_asset.label')"
        :error-messages="toMessages(v$.feeAsset)"
      />
    </div>

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextArea
      v-model="notes[0]"
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

    <RuiTextArea
      v-if="notes.length === 2"
      v-model="notes[1]"
      prepend-icon="lu-sticky-note"
      data-cy="fee-notes"
      variant="outlined"
      color="primary"
      max-rows="5"
      min-rows="3"
      auto-grow
      class="mt-4"
      :label="t('swap_event_form.fee_notes')"
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
