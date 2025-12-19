<script setup lang="ts">
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import type { EvmHistoryEvent, NewEvmHistoryEventPayload } from '@/types/history/events/schemas';
import { HistoryEventEntryType, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';
import AmountInput from '@/components/inputs/AmountInput.vue';
import CounterpartyInput from '@/components/inputs/CounterpartyInput.vue';
import JsonInput from '@/components/inputs/JsonInput.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useEditModeStateTracker } from '@/composables/history/events/edit-mode-state';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { useSupportedChains } from '@/composables/info/chains';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import EvmLocation from '@/modules/history/management/forms/common/EvmLocation.vue';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { toMessages } from '@/utils/validation';

interface HistoryEventFormProps {
  data: StandaloneEventData<EvmHistoryEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<HistoryEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

const { data } = toRefs(props);

const { counterparties } = useHistoryEventCounterpartyMappings();

const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);

const assetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('assetPriceForm');

const txRef = ref<string>('');
const groupIdentifier = ref<string>('');
const sequenceIndex = ref<string>('');
const timestamp = ref<number>(0);
const location = ref<string>('');
const eventType = ref<string>('');
const eventSubtype = ref<string>('none');
const asset = ref<string>('');
const amount = ref<string>('');
const address = ref<string>('');
const locationLabel = ref<string>('');
const notes = ref<string>('');
const counterparty = ref<string>('');
const extraData = ref<object>({});

const errorMessages = ref<Record<string, string[]>>({});

const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const isInformationalEvent = computed(() => get(eventType) === 'informational');

const rules = {
  address: commonRules.createValidEthAddressRule(),
  amount: commonRules.createRequiredAmountRule(),
  asset: commonRules.createRequiredAssetRule(),
  counterparty: commonRules.createValidCounterpartyRule(counterparties),
  eventSubtype: commonRules.createRequiredEventSubtypeRule(),
  eventType: commonRules.createRequiredEventTypeRule(),
  groupIdentifier: commonRules.createRequiredGroupIdentifierRule(() => get(data).type === 'edit'),
  location: commonRules.createRequiredLocationRule(),
  locationLabel: commonRules.createExternalValidationRule(),
  notes: commonRules.createExternalValidationRule(),
  sequenceIndex: commonRules.createRequiredSequenceIndexRule(),
  timestamp: commonRules.createExternalValidationRule(),
  txRef: commonRules.createValidTxHashRule(),
};

const numericAmount = bigNumberifyFromRef(amount);

const { saveHistoryEventHandler } = useHistoryEventsForm();
const { txChainsToLocation } = useSupportedChains();
const { captureEditModeStateFromRefs, shouldSkipSaveFromRefs } = useEditModeStateTracker();

const states = {
  address,
  amount,
  asset,
  counterparty,
  eventSubtype,
  eventType,
  extraData,
  groupIdentifier,
  location,
  locationLabel,
  notes,
  sequenceIndex,
  timestamp,
  txRef,
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

function reset() {
  set(sequenceIndex, get(data)?.nextSequenceId || '0');
  set(txRef, '');
  set(groupIdentifier, null);
  set(timestamp, dayjs().valueOf());
  set(location, get(lastLocation));
  set(address, '');
  set(locationLabel, '');
  set(eventType, '');
  set(eventSubtype, 'none');
  set(asset, '');
  set(amount, '0');
  set(notes, '');
  set(counterparty, '');
  set(extraData, {});
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
}

function applyEditableData(entry: EvmHistoryEvent) {
  set(sequenceIndex, entry.sequenceIndex?.toString() ?? '');
  set(txRef, entry.txRef);
  set(groupIdentifier, entry.groupIdentifier);
  set(timestamp, entry.timestamp);
  set(location, entry.location);
  set(eventType, entry.eventType);
  set(eventSubtype, entry.eventSubtype || 'none');
  set(asset, entry.asset);
  set(amount, entry.amount.toFixed());
  set(address, entry.address ?? '');
  set(locationLabel, entry.locationLabel ?? '');
  set(notes, entry.userNotes ?? '');
  set(counterparty, entry.counterparty ?? '');
  set(extraData, entry.extraData || {});

  // Capture state snapshot for edit mode comparison
  captureEditModeStateFromRefs(states);
}

function applyGroupHeaderData(entry: EvmHistoryEvent) {
  set(sequenceIndex, get(data)?.nextSequenceId || '0');
  set(groupIdentifier, entry.groupIdentifier);
  set(location, entry.location || get(lastLocation));
  set(address, entry.address ?? '');
  set(locationLabel, entry.locationLabel ?? '');
  set(txRef, entry.txRef);
  set(timestamp, entry.timestamp);
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const eventData = get(data);
  const editable = eventData.type === 'edit' ? eventData.event : undefined;
  const userNotes = get(notes).trim();

  const payload: NewEvmHistoryEventPayload = {
    address: get(address) || null,
    amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
    asset: get(asset),
    counterparty: get(counterparty) || null,
    entryType: HistoryEventEntryType.EVM_EVENT,
    eventSubtype: get(eventSubtype),
    eventType: get(eventType),
    extraData: get(extraData) || null,
    groupIdentifier: get(groupIdentifier) ?? null,
    location: get(location),
    locationLabel: get(locationLabel) || null,
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp: get(timestamp),
    txRef: get(txRef),
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
      <EventDateLocation
        v-model:timestamp="timestamp"
        v-model:location="location"
        class="col-span-2"
        :location-disabled="data.type !== 'add'"
        :locations="txChainsToLocation"
        :error-messages="{
          location: toMessages(v$.location),
          timestamp: toMessages(v$.timestamp),
        }"
        @blur="v$[$event].$touch()"
      />
    </div>

    <RuiTextField
      v-model="txRef"
      variant="outlined"
      color="primary"
      :disabled="data.type !== 'add'"
      data-cy="tx-ref"
      :label="t('common.tx_hash')"
      required
      :error-messages="toMessages(v$.txRef)"
      @blur="v$.txRef.$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventTypeForm
      v-model:event-type="eventType"
      v-model:event-subtype="eventSubtype"
      :counterparty="counterparty"
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
      :no-price-fields="isInformationalEvent"
    />

    <RuiDivider class="mb-6 mt-2" />

    <EvmLocation
      v-model:location-label="locationLabel"
      v-model:address="address"
      :location="location"
      :error-messages="{
        locationLabel: toMessages(v$.locationLabel),
        address: toMessages(v$.address),
      }"
      @blur="v$[$event].$touch()"
    />

    <div class="grid md:grid-cols-2 gap-4">
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
      <CounterpartyInput
        v-model="counterparty"
        :label="t('common.counterparty')"
        data-cy="counterparty"
        :error-messages="toMessages(v$.counterparty)"
        @blur="v$.counterparty.$touch()"
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
        data-cy="evm-event-form__advance"
        header-class="py-4"
        eager
      >
        <template #header>
          {{ t('transactions.events.form.advanced') }}
        </template>
        <div class="py-2">
          <RuiTextField
            v-model="groupIdentifier"
            variant="outlined"
            color="primary"
            data-cy="groupIdentifier"
            :label="t('transactions.events.form.event_identifier.label')"
            :error-messages="toMessages(v$.groupIdentifier)"
            @blur="v$.groupIdentifier.$touch()"
          />

          <JsonInput
            v-model="extraData"
            :label="t('transactions.events.form.extra_data.label')"
          />
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>
