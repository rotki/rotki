<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import dayjs from 'dayjs';
import { helpers, required } from '@vuelidate/validators';
import {
  type EvmHistoryEvent,
  type NewEvmHistoryEventPayload
} from '@/types/history/events';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { type Writeable } from '@/types';
import { type ActionDataEntry } from '@/types/action';
import { toMessages } from '@/utils/validation';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';

const props = withDefaults(
  defineProps<{
    editableItem: EvmHistoryEvent | null;
    nextSequence?: string | null;
    groupHeader: EvmHistoryEvent | null;
  }>(),
  {
    nextSequence: ''
  }
);

const { t } = useI18n();

const { editableItem, groupHeader, nextSequence } = toRefs(props);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const {
  counterparties,
  getEventTypeData,
  historyEventTypesData,
  historyEventSubTypesData,
  historyEventTypeGlobalMapping,
  historyEventTypePerProtocolMapping,
  historyEventProductsMapping
} = useHistoryEventMappings();

const lastLocation = useLocalStorage(
  'rotki.history_event.location',
  TRADE_LOCATION_EXTERNAL
);

const assetPriceForm: Ref<InstanceType<
  typeof HistoryEventAssetPriceForm
> | null> = ref(null);

const txHash: Ref<string> = ref('');
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
const counterparty: Ref<string> = ref('');
const product: Ref<string> = ref('');

const transactionEventType: Ref<string | null> = ref('');

const errorMessages = ref<Record<string, string[]>>({});

const externalServerValidation = () => true;

const rules = {
  timestamp: { externalServerValidation },
  locationLabel: { externalServerValidation },
  notes: { externalServerValidation },
  txHash: {
    required: helpers.withMessage(
      t('transactions.events.form.tx_hash.validation.non_empty').toString(),
      required
    ),
    isValid: helpers.withMessage(
      t('transactions.events.form.tx_hash.validation.valid').toString(),
      (value: string) => isValidTxHash(value)
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
  },
  counterparty: {
    isValid: helpers.withMessage(
      t('transactions.events.form.counterparty.validation.valid').toString(),
      (value: string) =>
        !value ||
        get(counterparties).includes(value) ||
        isValidEthAddress(value)
    )
  },
  product: {
    isValid: helpers.withMessage(
      t('transactions.events.form.product.validation.valid').toString(),
      (value: string) =>
        !value || get(historyEventLimitedProducts).includes(value)
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
    txHash,
    location,
    asset,
    amount,
    usdValue,
    sequenceIndex,
    eventType,
    eventSubtype,
    counterparty,
    product
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages
  }
);

const reset = () => {
  set(sequenceIndex, get(nextSequence) ?? '0');
  set(txHash, '');
  set(datetime, convertFromTimestamp(dayjs().unix(), true));
  set(location, get(lastLocation));
  set(locationLabel, '');
  set(eventType, '');
  set(eventSubtype, '');
  set(asset, '');
  set(amount, '0');
  set(usdValue, '0');
  set(notes, '');
  set(counterparty, '');
  set(product, '');
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
};

const applyEditableData = async (entry: EvmHistoryEvent) => {
  set(sequenceIndex, entry.sequenceIndex?.toString() ?? '');
  set(txHash, entry.txHash);
  set(datetime, convertFromTimestamp(entry.timestamp, true));
  set(location, entry.location);
  set(eventType, entry.eventType);
  set(eventSubtype, entry.eventSubtype || 'none');
  set(asset, entry.asset);
  set(amount, entry.balance.amount.toFixed());
  set(usdValue, entry.balance.usdValue.toFixed());
  set(locationLabel, entry.locationLabel ?? '');
  set(notes, entry.notes ?? '');
  set(counterparty, entry.counterparty ?? '');
  set(product, entry.product ?? '');
};

const applyGroupHeaderData = async (entry: EvmHistoryEvent) => {
  set(sequenceIndex, get(nextSequence) ?? '0');
  set(location, entry.location || get(lastLocation));
  set(locationLabel, entry.locationLabel ?? '');
  set(txHash, entry.txHash);
  set(datetime, convertFromTimestamp(entry.timestamp, true));
};

const { setMessage } = useMessageStore();

const { editHistoryEvent, addHistoryEvent } = useHistoryTransactions();
const save = async (): Promise<boolean> => {
  const timestamp = convertToTimestamp(get(datetime));
  const assetVal = get(asset);

  const payload: Writeable<NewEvmHistoryEventPayload> = {
    entryType: HistoryEventEntryType.EVM_EVENT,
    txHash: get(txHash),
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
    notes: get(notes) || undefined,
    counterparty: get(counterparty) || null,
    product: get(product) || null
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
  [eventType, eventSubtype, counterparty, location],
  ([eventType, eventSubtype, counterparty, location]) => {
    const typeData = get(
      getEventTypeData(
        {
          eventType,
          eventSubtype,
          counterparty,
          location,
          entryType: HistoryEventEntryType.EVM_EVENT
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
    const perProtocolMapping = get(historyEventTypePerProtocolMapping);
    const counterpartyVal = get(counterparty);
    const locationVal = get(location);

    if (!eventTypeVal) {
      return allData;
    }

    let globalMappingKeys: string[] = [];

    const globalMappingFound = globalMapping[eventTypeVal];
    if (globalMappingFound) {
      globalMappingKeys = Object.keys(globalMappingFound);
    }

    let perProtocolMappingKeys: string[] = [];

    if (locationVal && counterpartyVal) {
      const perProtocolMappingObj =
        perProtocolMapping?.[locationVal]?.[counterpartyVal]?.[eventTypeVal];
      if (perProtocolMappingObj) {
        perProtocolMappingKeys = Object.keys(perProtocolMappingObj);
      }
    }

    return allData.filter(
      (data: ActionDataEntry) =>
        globalMappingKeys.includes(data.identifier) ||
        perProtocolMappingKeys.includes(data.identifier)
    );
  });

const historyEventLimitedProducts: ComputedRef<string[]> = computed(() => {
  const counterpartyVal = get(counterparty);
  const mapping = get(historyEventProductsMapping);

  if (!counterpartyVal) {
    return [];
  }

  return mapping[counterpartyVal] ?? [];
});

watch(historyEventLimitedProducts, products => {
  const selected = get(product);
  if (!products.includes(selected)) {
    set(product, '');
  }
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
      v-model="txHash"
      outlined
      :disabled="!!(editableItem || groupHeader)"
      data-cy="txHash"
      :label="t('common.tx_hash')"
      :error-messages="toMessages(v$.txHash)"
      @blur="v$.txHash.$touch()"
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
      <ComboboxWithCustomInput
        v-model="counterparty"
        outlined
        required
        clearable
        auto-select-first
        :label="t('transactions.events.form.counterparty.label')"
        :items="counterparties"
        data-cy="counterparty"
        :error-messages="toMessages(v$.counterparty)"
        @blur="v$.counterparty.$touch()"
      />
      <VAutocomplete
        v-model="product"
        clearable
        outlined
        required
        auto-select-first
        :disabled="historyEventLimitedProducts.length === 0"
        :label="t('transactions.events.form.product.label')"
        :items="historyEventLimitedProducts"
        data-cy="product"
        :error-messages="toMessages(v$.product)"
        @blur="v$.product.$touch()"
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
