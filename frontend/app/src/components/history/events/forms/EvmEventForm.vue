<script setup lang="ts">
import type { EvmHistoryEvent, NewEvmHistoryEventPayload } from '@/types/history/events';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';
import HistoryEventTypeForm from '@/components/history/events/forms/HistoryEventTypeForm.vue';
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
import { useBlockchainStore } from '@/store/blockchain';
import { DateFormat } from '@/types/date-format';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { toMessages } from '@/utils/validation';
import { Blockchain, HistoryEventEntryType, isValidEthAddress, isValidTxHash, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';

interface HistoryEventFormProps {
  editableItem?: EvmHistoryEvent;
  nextSequence?: string;
  groupHeader?: EvmHistoryEvent;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = withDefaults(defineProps<HistoryEventFormProps>(), {
  editableItem: undefined,
  groupHeader: undefined,
  nextSequence: '',
});

const { t } = useI18n();

const { editableItem, groupHeader, nextSequence } = toRefs(props);

const { historyEventProductsMapping } = useHistoryEventProductMappings();
const { counterparties } = useHistoryEventCounterpartyMappings();

const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);

const assetPriceForm = ref<InstanceType<typeof HistoryEventAssetPriceForm>>();

const txHash = ref<string>('');
const eventIdentifier = ref<string>('');
const sequenceIndex = ref<string>('');
const datetime = ref<string>('');
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

const externalServerValidation = () => true;

const isInformationalEvent = computed(() => get(eventType) === 'informational');

const historyEventLimitedProducts = computed<string[]>(() => {
  const counterpartyVal = get(counterparty);
  const mapping = get(historyEventProductsMapping);

  if (!counterpartyVal)
    return [];

  return mapping[counterpartyVal] ?? [];
});

const rules = {
  address: {
    isValid: helpers.withMessage(
      t('transactions.events.form.address.validation.valid'),
      (value: string) => !value || isValidEthAddress(value),
    ),
  },
  amount: {
    required: helpers.withMessage(t('transactions.events.form.amount.validation.non_empty'), required),
  },
  asset: {
    required: helpers.withMessage(t('transactions.events.form.asset.validation.non_empty'), required),
  },
  counterparty: {
    isValid: helpers.withMessage(
      t('transactions.events.form.counterparty.validation.valid'),
      (value: string) => !value || get(counterparties).includes(value) || isValidEthAddress(value),
    ),
  },
  eventIdentifier: {
    required: helpers.withMessage(
      t('transactions.events.form.event_identifier.validation.non_empty'),
      requiredIf(() => !!get(editableItem)),
    ),
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
  product: {
    isValid: helpers.withMessage(
      t('transactions.events.form.product.validation.valid'),
      (value: string) => !value || get(historyEventLimitedProducts).includes(value),
    ),
  },
  sequenceIndex: {
    required: helpers.withMessage(t('transactions.events.form.sequence_index.validation.non_empty'), required),
  },
  timestamp: { externalServerValidation },
  txHash: {
    isValid: helpers.withMessage(t('transactions.events.form.tx_hash.validation.valid'), (value: string) =>
      isValidTxHash(value)),
    required: helpers.withMessage(t('transactions.events.form.tx_hash.validation.non_empty'), required),
  },
};

const numericAmount = bigNumberifyFromRef(amount);

const { getPayloadNotes, saveHistoryEventHandler } = useHistoryEventsForm();
const { getAddresses } = useBlockchainStore();
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
  timestamp: datetime,
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
  set(sequenceIndex, get(nextSequence) || '0');
  set(txHash, '');
  set(eventIdentifier, null);
  set(datetime, convertFromTimestamp(dayjs().valueOf(), DateFormat.DateMonthYearHourMinuteSecond, true));
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
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
  set(location, entry.location);
  set(eventType, entry.eventType);
  set(eventSubtype, entry.eventSubtype || 'none');
  set(asset, entry.asset);
  set(amount, entry.amount.toFixed());
  set(address, entry.address ?? '');
  set(locationLabel, entry.locationLabel ?? '');
  set(notes, entry.notes ?? '');
  set(counterparty, entry.counterparty ?? '');
  set(product, entry.product ?? '');
  set(extraData, entry.extraData || {});
}

function applyGroupHeaderData(entry: EvmHistoryEvent) {
  set(sequenceIndex, get(nextSequence) || '0');
  set(eventIdentifier, entry.eventIdentifier);
  set(location, entry.location || get(lastLocation));
  set(address, entry.address ?? '');
  set(locationLabel, entry.locationLabel ?? '');
  set(txHash, entry.txHash);
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const timestamp = convertToTimestamp(get(datetime), DateFormat.DateMonthYearHourMinuteSecond, true);

  const editable = get(editableItem);
  const usedNotes = getPayloadNotes(get(notes), editable?.notes);

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
    notes: usedNotes ? usedNotes.trim() : undefined,
    product: get(product) || null,
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp,
    txHash: get(txHash),
  };

  return await saveHistoryEventHandler(
    editable ? { ...payload, identifier: editable.identifier } : payload,
    assetPriceForm,
    errorMessages,
    reset,
  );
}

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

watch(location, (location: string) => {
  if (location)
    set(lastLocation, location);
});

watch([groupHeader, editableItem], checkPropsData);

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
        :items="txChainsToLocation"
        :disabled="!!(editableItem || groupHeader)"
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
      :disabled="!!(editableItem || groupHeader)"
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
      :datetime="datetime"
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
