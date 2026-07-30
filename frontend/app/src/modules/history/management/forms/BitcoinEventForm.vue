<script setup lang="ts">
import type { BitcoinEvent, NewBitcoinEventPayload } from '@/modules/history/events/schemas';
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';
import { bigNumberifyFromRef } from '@/modules/core/common/data/bignumbers';
import { useFormStateWatcher } from '@/modules/core/common/use-form';
import { toMessages } from '@/modules/core/common/validation/validation';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { useEditModeStateTracker } from '@/modules/history/events/use-edit-mode-state-tracker';
import { useHistoryEventsForm } from '@/modules/history/events/use-history-events-form';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import JsonInput from '@/modules/shell/components/inputs/JsonInput.vue';

interface HistoryEventFormProps {
  data: StandaloneEventData<BitcoinEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<HistoryEventFormProps>();

const BITCOIN_LOCATIONS = ['bitcoin', 'bitcoin_cash'];

const { t } = useI18n({ useScope: 'global' });

const { counterparties } = useHistoryEventCounterpartyMappings();

const assetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('assetPriceForm');

const txRef = ref<string>('');
const groupIdentifier = ref<string>('');
const hasActualGroupIdentifier = ref<boolean>(false);
const sequenceIndex = ref<string>('');
const timestamp = ref<number>(0);
const location = ref<string>(BITCOIN_LOCATIONS[0]);
const eventType = ref<string>('');
const eventSubtype = ref<string>('none');
const amount = ref<string>('');
const locationLabel = ref<string>('');
const notes = ref<string>('');
const counterparty = ref<string>();
const extraData = ref<object>({});

const errorMessages = ref<Record<string, string[]>>({});

const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const isInformationalEvent = computed(() => get(eventType) === 'informational');

// A bitcoin transaction only ever moves the asset of its own chain, so the asset follows
// the location instead of being picked. The backend refuses anything else.
const asset = computed<string>(() => get(location) === BITCOIN_LOCATIONS[1] ? 'BCH' : 'BTC');

const rules = {
  amount: commonRules.createRequiredAmountRule(),
  asset: commonRules.createRequiredAssetRule(),
  counterparty: commonRules.createValidCounterpartyRule(counterparties),
  eventSubtype: commonRules.createRequiredEventSubtypeRule(),
  eventType: commonRules.createRequiredEventTypeRule(),
  groupIdentifier: commonRules.createRequiredGroupIdentifierRule(() => data.type === 'edit'),
  location: commonRules.createRequiredLocationRule(),
  locationLabel: commonRules.createExternalValidationRule(),
  notes: commonRules.createExternalValidationRule(),
  sequenceIndex: commonRules.createRequiredSequenceIndexRule(),
  timestamp: commonRules.createExternalValidationRule(),
  txRef: commonRules.createValidBitcoinTxIdRule(),
};

const numericAmount = bigNumberifyFromRef(amount);

const { saveHistoryEventHandler } = useHistoryEventsForm();
const { captureEditModeStateFromRefs, shouldSkipSaveFromRefs } = useEditModeStateTracker();

const states = {
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
  set(sequenceIndex, data?.nextSequenceId || '0');
  set(txRef, '');
  set(groupIdentifier, null);
  set(hasActualGroupIdentifier, false);
  set(timestamp, dayjs().valueOf());
  set(locationLabel, '');
  set(eventType, '');
  set(eventSubtype, 'none');
  set(amount, '0');
  set(notes, '');
  set(counterparty, undefined);
  set(extraData, {});
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
}

function applyEditableData(entry: BitcoinEvent) {
  set(sequenceIndex, entry.sequenceIndex?.toString() ?? '');
  set(txRef, entry.txRef);
  const hasActual = !!entry.actualGroupIdentifier;
  set(hasActualGroupIdentifier, hasActual);
  set(groupIdentifier, hasActual ? entry.actualGroupIdentifier! : entry.groupIdentifier);
  set(timestamp, entry.timestamp);
  set(location, entry.location);
  set(eventType, entry.eventType);
  set(eventSubtype, entry.eventSubtype || 'none');
  set(amount, entry.amount.toFixed());
  set(locationLabel, entry.locationLabel ?? '');
  set(notes, entry.userNotes ?? '');
  set(counterparty, entry.counterparty ?? undefined);
  set(extraData, entry.extraData || {});

  // Capture state snapshot for edit mode comparison
  captureEditModeStateFromRefs(states);
}

function applyGroupHeaderData(entry: BitcoinEvent) {
  set(sequenceIndex, data?.nextSequenceId || '0');
  set(groupIdentifier, entry.groupIdentifier);
  set(locationLabel, entry.locationLabel ?? '');
  set(txRef, entry.txRef);
  set(timestamp, entry.timestamp);
  set(location, entry.location);
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

/** Empty form fields are normalised to the nulls and defaults the backend expects. */
function buildPayload(): NewBitcoinEventPayload {
  const userNotes = get(notes).trim();

  return {
    amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
    asset: get(asset),
    counterparty: get(counterparty) || '',
    entryType: HistoryEventEntryType.BITCOIN_EVENT,
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
}

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const editable = data.type === 'edit' ? data.event : undefined;
  const payload = buildPayload();

  return await saveHistoryEventHandler(
    editable ? { ...payload, identifier: editable.identifier } : payload,
    assetPriceForm,
    errorMessages,
    reset,
    shouldSkipSaveFromRefs(!!editable, states),
  );
}

function checkPropsData() {
  if (data.type === 'edit') {
    applyEditableData(data.event);
    return;
  }

  if (data.type === 'group-add') {
    applyGroupHeaderData(data.group);
    return;
  }
  reset();
}

watch(() => data, checkPropsData);

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
    <HistoryEventTypeForm
      v-model:event-type="eventType"
      v-model:event-subtype="eventSubtype"
      :counterparty="counterparty"
      :entry-type="HistoryEventEntryType.BITCOIN_EVENT"
      :v$="v$"
      show-accounting-rule-link
      :dirty="stateUpdated"
      class="mb-4"
    />

    <div class="grid md:grid-cols-2 gap-4 mb-4">
      <EventDateLocation
        v-model:timestamp="timestamp"
        v-model:location="location"
        class="col-span-2"
        :locations="BITCOIN_LOCATIONS"
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
      :label="t('transactions.events.form.tx_id.label')"
      required
      :error-messages="toMessages(v$.txRef)"
      @blur="v$.txRef.$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      ref="assetPriceForm"
      v-model:amount="amount"
      :asset="asset"
      disable-asset
      :location="location"
      :v$="v$"
      :timestamp="timestamp"
      :no-price-fields="isInformationalEvent"
    />

    <RuiDivider class="mb-6 mt-2" />

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
        data-cy="bitcoin-event-form__advance"
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
            :disabled="hasActualGroupIdentifier"
            :label="t('transactions.events.form.group_identifier.label')"
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
