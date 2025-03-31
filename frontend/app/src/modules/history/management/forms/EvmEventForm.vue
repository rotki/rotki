<script setup lang="ts">
import type { IndependentEventData } from '@/modules/history/management/forms/form-types';
import type { EvmHistoryEvent, NewEvmHistoryEventPayload } from '@/types/history/events';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import CounterpartyInput from '@/components/inputs/CounterpartyInput.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import JsonInput from '@/components/inputs/JsonInput.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { useHistoryEventProductMappings } from '@/composables/history/events/mapping/product';
import { useSupportedChains } from '@/composables/info/chains';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { toMessages } from '@/utils/validation';
import { Blockchain, HistoryEventEntryType, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';

interface HistoryEventFormProps {
  data: IndependentEventData<EvmHistoryEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<HistoryEventFormProps>();

const { t } = useI18n();

const { data } = toRefs(props);

const { historyEventProductsMapping } = useHistoryEventProductMappings();
const { counterparties } = useHistoryEventCounterpartyMappings();

const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);

const assetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('assetPriceForm');

const txHash = ref<string>('');
const eventIdentifier = ref<string>('');
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
const product = ref<string>('');
const extraData = ref<object>({});

const errorMessages = ref<Record<string, string[]>>({});

const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const isInformationalEvent = computed(() => get(eventType) === 'informational');

const historyEventLimitedProducts = computed<string[]>(() => {
  const counterpartyVal = get(counterparty);
  const mapping = get(historyEventProductsMapping);

  if (!counterpartyVal)
    return [];

  return mapping[counterpartyVal] ?? [];
});

const rules = {
  address: commonRules.createValidEthAddressRule(),
  amount: commonRules.createRequiredAmountRule(),
  asset: commonRules.createRequiredAssetRule(),
  counterparty: commonRules.createValidCounterpartyRule(counterparties),
  eventIdentifier: commonRules.createRequiredEventIdentifierRule(() => get(data).type === 'edit'),
  eventSubtype: commonRules.createRequiredEventSubtypeRule(),
  eventType: commonRules.createRequiredEventTypeRule(),
  location: commonRules.createRequiredLocationRule(),
  locationLabel: commonRules.createExternalValidationRule(),
  notes: commonRules.createExternalValidationRule(),
  product: commonRules.createValidProductRule(historyEventLimitedProducts),
  sequenceIndex: commonRules.createRequiredSequenceIndexRule(),
  timestamp: commonRules.createExternalValidationRule(),
  txHash: commonRules.createValidTxHashRule(),
};

const numericAmount = bigNumberifyFromRef(amount);

const { saveHistoryEventHandler } = useHistoryEventsForm();
const { getAddresses } = useAccountAddresses();
const { txChainsToLocation } = useSupportedChains();

const states = {
  address,
  amount,
  asset,
  counterparty,
  eventIdentifier,
  eventSubtype,
  eventType,
  location,
  locationLabel,
  notes,
  product,
  sequenceIndex,
  timestamp,
  txHash,
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

const addressSuggestions = computed(() => getAddresses(Blockchain.ETH));

function reset() {
  set(sequenceIndex, get(data)?.nextSequenceId || '0');
  set(txHash, '');
  set(eventIdentifier, null);
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
  set(product, '');
  set(extraData, {});
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
}

function applyEditableData(entry: EvmHistoryEvent) {
  set(sequenceIndex, entry.sequenceIndex?.toString() ?? '');
  set(txHash, entry.txHash);
  set(eventIdentifier, entry.eventIdentifier);
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
  set(product, entry.product ?? '');
  set(extraData, entry.extraData || {});
}

function applyGroupHeaderData(entry: EvmHistoryEvent) {
  set(sequenceIndex, get(data)?.nextSequenceId || '0');
  set(eventIdentifier, entry.eventIdentifier);
  set(location, entry.location || get(lastLocation));
  set(address, entry.address ?? '');
  set(locationLabel, entry.locationLabel ?? '');
  set(txHash, entry.txHash);
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
    eventIdentifier: get(eventIdentifier) ?? null,
    eventSubtype: get(eventSubtype),
    eventType: get(eventType),
    extraData: get(extraData) || null,
    location: get(location),
    locationLabel: get(locationLabel) || null,
    product: get(product) || null,
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp: get(timestamp),
    txHash: get(txHash),
    userNotes: userNotes.length > 0 ? userNotes : undefined,
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

watch(historyEventLimitedProducts, (products) => {
  const selected = get(product);
  if (!products.includes(selected))
    set(product, '');
});

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
        v-model="timestamp"
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
        :items="txChainsToLocation"
        :disabled="data.type !== 'add'"
        data-cy="location"
        :label="t('common.location')"
        :error-messages="toMessages(v$.location)"
        @blur="v$.location.$touch()"
      />
    </div>

    <RuiTextField
      v-model="txHash"
      variant="outlined"
      color="primary"
      :disabled="data.type !== 'add'"
      data-cy="txHash"
      :label="t('common.tx_hash')"
      :error-messages="toMessages(v$.txHash)"
      @blur="v$.txHash.$touch()"
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
      :v$="v$"
      :timestamp="timestamp"
      :hide-price-fields="isInformationalEvent"
    />

    <RuiDivider class="mb-6 mt-2" />

    <div class="grid md:grid-cols-2 gap-4">
      <AutoCompleteWithSearchSync
        v-model="locationLabel"
        :items="addressSuggestions"
        clearable
        data-cy="locationLabel"
        :label="t('transactions.events.form.location_label.label')"
        :error-messages="toMessages(v$.locationLabel)"
        auto-select-first
        @blur="v$.locationLabel.$touch()"
      />

      <AutoCompleteWithSearchSync
        v-model="address"
        :items="addressSuggestions"
        clearable
        data-cy="address"
        :label="t('transactions.events.form.address.label')"
        :error-messages="toMessages(v$.address)"
        auto-select-first
        @blur="v$.address.$touch()"
      />
    </div>
    <div class="grid md:grid-cols-3 gap-4">
      <AmountInput
        v-model="sequenceIndex"
        variant="outlined"
        integer
        data-cy="sequenceIndex"
        :label="t('transactions.events.form.sequence_index.label')"
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
      <RuiAutoComplete
        v-model="product"
        clearable
        variant="outlined"
        auto-select-first
        :disabled="historyEventLimitedProducts.length === 0"
        :label="t('transactions.events.form.product.label')"
        :options="historyEventLimitedProducts"
        data-cy="product"
        :error-messages="toMessages(v$.product)"
        @blur="v$.product.$touch()"
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
            v-model="eventIdentifier"
            variant="outlined"
            color="primary"
            data-cy="eventIdentifier"
            :label="t('transactions.events.form.event_identifier.label')"
            :error-messages="toMessages(v$.eventIdentifier)"
            @blur="v$.eventIdentifier.$touch()"
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
