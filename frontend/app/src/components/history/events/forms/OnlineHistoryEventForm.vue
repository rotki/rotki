<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import dayjs from 'dayjs';
import { helpers, required } from '@vuelidate/validators';
import { isEmpty } from 'lodash-es';
import {
  type NewOnlineHistoryEventPayload,
  type OnlineHistoryEvent
} from '@/types/history/events';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { type ActionDataEntry } from '@/types/action';
import { toMessages } from '@/utils/validation';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';
import { DateFormat } from '@/types/date-format';

const props = withDefaults(
  defineProps<{
    editableItem?: OnlineHistoryEvent | null;
    nextSequence?: string | null;
    groupHeader?: OnlineHistoryEvent | null;
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
  getEventTypeData,
  historyEventTypesData,
  historyEventSubTypesData,
  historyEventTypeGlobalMapping
} = useHistoryEventMappings();

const lastLocation = useLocalStorage(
  'rotki.history_event.location',
  TRADE_LOCATION_EXTERNAL
);

const assetPriceForm: Ref<InstanceType<
  typeof HistoryEventAssetPriceForm
> | null> = ref(null);

const eventIdentifier: Ref<string> = ref('');
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

const errorMessages = ref<Record<string, string[]>>({});

const externalServerValidation = () => true;

const rules = {
  timestamp: { externalServerValidation },
  locationLabel: { externalServerValidation },
  notes: { externalServerValidation },
  eventIdentifier: {
    required: helpers.withMessage(
      t(
        'transactions.events.form.event_identifier.validation.non_empty'
      ).toString(),
      required
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
    location,
    asset,
    amount,
    usdValue,
    sequenceIndex,
    eventType,
    eventSubtype
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages
  }
);

const reset = () => {
  set(sequenceIndex, get(nextSequence) || '0');
  set(eventIdentifier, '');
  set(
    datetime,
    convertFromTimestamp(
      dayjs().valueOf(),
      DateFormat.DateMonthYearHourMinuteSecond,
      true
    )
  );
  set(location, get(lastLocation));
  set(locationLabel, '');
  set(eventType, '');
  set(eventSubtype, '');
  set(asset, '');
  set(amount, '0');
  set(usdValue, '0');
  set(notes, '');
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
};

const applyEditableData = async (entry: OnlineHistoryEvent) => {
  set(sequenceIndex, entry.sequenceIndex?.toString() ?? '');
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
  set(locationLabel, entry.locationLabel ?? '');
  set(notes, entry.notes ?? '');
};

const applyGroupHeaderData = async (entry: OnlineHistoryEvent) => {
  set(sequenceIndex, get(nextSequence) || '0');
  set(location, entry.location || get(lastLocation));
  set(locationLabel, entry.locationLabel ?? '');
  set(eventIdentifier, entry.eventIdentifier);
  set(
    datetime,
    convertFromTimestamp(
      entry.timestamp,
      DateFormat.DateMonthYearHourMinuteSecond,
      true
    )
  );
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

  const payload: NewOnlineHistoryEventPayload = {
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventIdentifier: get(eventIdentifier),
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
    locationLabel: get(locationLabel) || null,
    notes: get(notes) || undefined
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
        eventSubtype: get(eventSubtype)
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

    if (!eventTypeVal) {
      return allData;
    }

    let globalMappingKeys: string[] = [];

    const globalMappingFound = globalMapping[eventTypeVal];
    if (globalMappingFound) {
      globalMappingKeys = Object.keys(globalMappingFound);
    }

    return allData.filter((data: ActionDataEntry) =>
      globalMappingKeys.includes(data.identifier)
    );
  });

const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
const locationLabelSuggestions = computed(() =>
  get(connectedExchanges)
    .map(item => item.name)
    .filter(item => !!item)
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
        :disabled="!!(editableItem || groupHeader)"
        data-cy="location"
        :label="t('common.location')"
        :error-messages="toMessages(v$.location)"
        @blur="v$.location.$touch()"
      />
    </div>

    <VTextField
      v-model="eventIdentifier"
      outlined
      :disabled="!!(editableItem || groupHeader)"
      data-cy="eventIdentifier"
      :label="t('transactions.events.form.event_identifier.label')"
      :error-messages="toMessages(v$.eventIdentifier)"
      @blur="v$.eventIdentifier.$touch()"
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
        :items="locationLabelSuggestions"
        outlined
        clearable
        data-cy="locationLabel"
        :label="t('transactions.events.form.location_label.label')"
        :error-messages="toMessages(v$.locationLabel)"
        auto-select-first
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
  </div>
</template>
