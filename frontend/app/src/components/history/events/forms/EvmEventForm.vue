<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import dayjs from 'dayjs';
import { helpers, required } from '@vuelidate/validators';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { isEmpty } from 'lodash-es';
import {
  type EvmHistoryEvent,
  type NewEvmHistoryEventPayload
} from '@/types/history/events';
import {
  TRADE_LOCATION_ETHEREUM,
  TRADE_LOCATION_EXTERNAL
} from '@/data/defaults';
import { type ActionDataEntry } from '@/types/action';
import { toMessages } from '@/utils/validation';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';

const props = withDefaults(
  defineProps<{
    editableItem?: EvmHistoryEvent | null;
    nextSequence?: string | null;
    groupHeader?: EvmHistoryEvent | null;
  }>(),
  {
    editableItem: null,
    nextSequence: '',
    groupHeader: null
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
  set(datetime, convertFromTimestamp(dayjs().unix()));
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
  set(datetime, convertFromTimestamp(entry.timestamp));
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
  set(location, entry.location || get(lastLocation));
  set(address, entry.address ?? '');
  set(locationLabel, entry.locationLabel ?? '');
  set(txHash, entry.txHash);
  set(datetime, convertFromTimestamp(entry.timestamp));
};

watch(errorMessages, errors => {
  if (!isEmpty(errors)) {
    get(v$).$validate();
  }
});

const save = async (): Promise<boolean> => {
  const timestamp = convertToTimestamp(get(datetime));

  const payload: NewEvmHistoryEventPayload = {
    entryType: HistoryEventEntryType.EVM_EVENT,
    txHash: get(txHash),
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp: timestamp * 1000,
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

const historyTypeCombination = computed(() =>
  get(
    getEventTypeData(
      {
        eventType: get(eventType),
        eventSubtype: get(eventSubtype),
        counterparty: get(counterparty),
        location: get(location),
        entryType: HistoryEventEntryType.EVM_EVENT
      },
      false
    )
  )
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

const { txEvmChains } = useSupportedChains();

const locationsFromTxEvmChains = computed(() => {
  const txEvmChainIds = get(txEvmChains).map(item => toHumanReadable(item.id));
  return [TRADE_LOCATION_ETHEREUM, ...txEvmChainIds];
});

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
        :items="locationsFromTxEvmChains"
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

    <div class="border-t dark:border-rui-grey-800 mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      ref="assetPriceForm"
      :v$="v$"
      :datetime="datetime"
      :asset.sync="asset"
      :amount.sync="amount"
      :usd-value.sync="usdValue"
    />

    <div class="border-t dark:border-rui-grey-800 my-10" />

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

      <div class="flex flex-col gap-1 -mt-2 md:pl-4 mb-3">
        <div class="text-caption">
          {{ t('transactions.events.form.resulting_combination.label') }}
        </div>
        <HistoryEventTypeCombination
          :type="historyTypeCombination"
          show-label
        />
      </div>
    </div>

    <div class="border-t dark:border-rui-grey-800 mb-6 mt-2" />

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

    <div class="border-t dark:border-rui-grey-800 mb-6 mt-2" />

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

    <div class="border-t dark:border-rui-grey-800 mb-2 mt-6" />

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
          <JsonInput
            v-model="extraData"
            :label="t('transactions.events.form.extra_data.label')"
          />
        </VExpansionPanelContent>
      </VExpansionPanel>
    </VExpansionPanels>
  </div>
</template>
