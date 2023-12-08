<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import dayjs from 'dayjs';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { isEmpty } from 'lodash-es';
import {
  type EvmHistoryEvent,
  type NewEvmHistoryEventPayload
} from '@/types/history/events';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { toMessages } from '@/utils/validation';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';
import { DateFormat } from '@/types/date-format';

const props = withDefaults(
  defineProps<{
    editableItem?: EvmHistoryEvent;
    nextSequence?: string;
    groupHeader?: EvmHistoryEvent;
  }>(),
  {
    editableItem: undefined,
    nextSequence: '',
    groupHeader: undefined
  }
);

const { t } = useI18n();

const { editableItem, groupHeader, nextSequence } = toRefs(props);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { counterparties, historyEventProductsMapping } =
  useHistoryEventMappings();

const lastLocation = useLocalStorage(
  'rotki.history_event.location',
  TRADE_LOCATION_EXTERNAL
);

const assetPriceForm: Ref<InstanceType<
  typeof HistoryEventAssetPriceForm
> | null> = ref(null);

const txHash: Ref<string> = ref('');
const eventIdentifier = ref<string>();
const sequenceIndex: Ref<string> = ref('');
const datetime: Ref<string> = ref('');
const location: Ref<string> = ref('');
const eventType: Ref<string> = ref('');
const eventSubtype: Ref<string> = ref('');
const asset: Ref<string> = ref('');
const amount: Ref<string> = ref('');
const usdValue: Ref<string> = ref('');
const address: Ref<string> = ref('');
const locationLabel: Ref<string> = ref('');
const notes: Ref<string> = ref('');
const counterparty: Ref<string> = ref('');
const product: Ref<string> = ref('');
const extraData: Ref<object> = ref({});

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
  eventIdentifier: {
    required: helpers.withMessage(
      t(
        'transactions.events.form.event_identifier.validation.non_empty'
      ).toString(),
      requiredIf(() => !!get(editableItem))
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
  address: {
    isValid: helpers.withMessage(
      t('transactions.events.form.address.validation.valid').toString(),
      (value: string) => !value || isValidEthAddress(value)
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

const { setValidation, setSubmitFunc, saveHistoryEventHandler } =
  useHistoryEventsForm();

const v$ = setValidation(
  rules,
  {
    timestamp: datetime,
    locationLabel,
    notes,
    eventIdentifier,
    txHash,
    location,
    asset,
    amount,
    usdValue,
    address,
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
  set(sequenceIndex, get(nextSequence) || '0');
  set(txHash, '');
  set(eventIdentifier, null);
  set(
    datetime,
    convertFromTimestamp(
      dayjs().valueOf(),
      DateFormat.DateMonthYearHourMinuteSecond,
      true
    )
  );
  set(location, get(lastLocation));
  set(address, '');
  set(locationLabel, '');
  set(eventType, '');
  set(eventSubtype, '');
  set(asset, '');
  set(amount, '0');
  set(usdValue, '0');
  set(notes, '');
  set(counterparty, '');
  set(product, '');
  set(extraData, {});
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
};

const applyEditableData = async (entry: EvmHistoryEvent) => {
  set(sequenceIndex, entry.sequenceIndex?.toString() ?? '');
  set(txHash, entry.txHash);
  set(eventIdentifier, entry.eventIdentifier);
  set(
    datetime,
    convertFromTimestamp(
      entry.timestamp,
      DateFormat.DateMonthYearHourMinuteSecond,
      true
    )
  );
  set(location, entry.location);
  set(eventType, entry.eventType);
  set(eventSubtype, entry.eventSubtype || 'none');
  set(asset, entry.asset);
  set(amount, entry.balance.amount.toFixed());
  set(usdValue, entry.balance.usdValue.toFixed());
  set(address, entry.address ?? '');
  set(locationLabel, entry.locationLabel ?? '');
  set(notes, entry.notes ?? '');
  set(counterparty, entry.counterparty ?? '');
  set(product, entry.product ?? '');
  set(extraData, entry.extraData || {});
};

const applyGroupHeaderData = async (entry: EvmHistoryEvent) => {
  set(sequenceIndex, get(nextSequence) || '0');
  set(eventIdentifier, entry.eventIdentifier);
  set(location, entry.location || get(lastLocation));
  set(address, entry.address ?? '');
  set(locationLabel, entry.locationLabel ?? '');
  set(txHash, entry.txHash);
  set(
    datetime,
    convertFromTimestamp(
      entry.timestamp,
      DateFormat.DateMonthYearHourMinuteSecond,
      true
    )
  );
  set(usdValue, '0');
};

watch(errorMessages, errors => {
  if (!isEmpty(errors)) {
    get(v$).$validate();
  }
});

const save = async (): Promise<boolean> => {
  const timestamp = convertToTimestamp(
    get(datetime),
    DateFormat.DateMonthYearHourMinuteSecond,
    true
  );

  const payload: NewEvmHistoryEventPayload = {
    entryType: HistoryEventEntryType.EVM_EVENT,
    txHash: get(txHash),
    eventIdentifier: get(eventIdentifier) ?? null,
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp,
    eventType: get(eventType),
    eventSubtype: get(eventSubtype),
    asset: get(asset),
    balance: {
      amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
      usdValue: get(numericUsdValue).isNaN() ? Zero : get(numericUsdValue)
    },
    location: get(location),
    address: get(address) || null,
    locationLabel: get(locationLabel) || null,
    notes: get(notes) || undefined,
    counterparty: get(counterparty) || null,
    product: get(product) || null,
    extraData: get(extraData) || null
  };

  const edit = get(editableItem);

  return await saveHistoryEventHandler(
    edit ? { ...payload, identifier: edit.identifier } : payload,
    assetPriceForm,
    errorMessages,
    reset
  );
};

setSubmitFunc(save);

const numericAmount = bigNumberifyFromRef(amount);
const numericUsdValue = bigNumberifyFromRef(usdValue);

watch(location, (location: string) => {
  if (location) {
    set(lastLocation, location);
  }
});

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

const { txEvmChainsToLocation } = useSupportedChains();

const { accounts } = useAccountBalances();

const addressSuggestions = computed(() =>
  get(accounts)
    .filter(item => item.chain === Blockchain.ETH)
    .map(item => item.address)
);
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
        :items="txEvmChainsToLocation"
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

    <HistoryEventAssetPriceForm
      ref="assetPriceForm"
      :v$="v$"
      :datetime="datetime"
      :asset.sync="asset"
      :amount.sync="amount"
      :usd-value.sync="usdValue"
    />

    <RuiDivider class="my-10" />

    <HistoryEventTypeForm
      :event-type.sync="eventType"
      :event-subtype.sync="eventSubtype"
      :counterparty="counterparty"
      :v$="v$"
    />

    <RuiDivider class="mb-6 mt-2" />

    <div class="grid md:grid-cols-2 gap-4">
      <ComboboxWithCustomInput
        v-model="locationLabel"
        :items="addressSuggestions"
        outlined
        clearable
        data-cy="locationLabel"
        :label="t('transactions.events.form.location_label.label')"
        :error-messages="toMessages(v$.locationLabel)"
        auto-select-first
        @blur="v$.locationLabel.$touch()"
      />

      <ComboboxWithCustomInput
        v-model="address"
        :items="addressSuggestions"
        outlined
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

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextArea
      v-model.trim="notes"
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

    <RuiDivider class="mb-2 mt-6" />

    <VExpansionPanels flat>
      <VExpansionPanel>
        <VExpansionPanelHeader
          class="p-0"
          data-cy="evm-event-form__advance-toggle"
        >
          {{ t('transactions.events.form.advanced') }}
        </VExpansionPanelHeader>
        <VExpansionPanelContent
          class="[&>.v-expansion-panel-content\_\_wrap]:!p-0"
        >
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
        </VExpansionPanelContent>
      </VExpansionPanel>
    </VExpansionPanels>
  </div>
</template>
