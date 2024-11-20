<script setup lang="ts">
import dayjs from 'dayjs';
import { Blockchain, HistoryEventEntryType } from '@rotki/common';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { isEmpty } from 'lodash-es';
import { toMessages } from '@/utils/validation';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';
import { DateFormat } from '@/types/date-format';
import type { EthBlockEvent, NewEthBlockEventPayload } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    editableItem?: EthBlockEvent;
    groupHeader?: EthBlockEvent;
  }>(),
  {
    editableItem: undefined,
    groupHeader: undefined,
  },
);

const { t } = useI18n();

const { editableItem, groupHeader } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const assetPriceForm = ref<InstanceType<typeof HistoryEventAssetPriceForm>>();

const eventIdentifier = ref<string>('');
const datetime = ref<string>('');
const amount = ref<string>('');
const usdValue = ref<string>('');
const blockNumber = ref<string>('');
const validatorIndex = ref<string>('');
const feeRecipient = ref<string>('');
const isMevReward = ref<boolean>(false);

const errorMessages = ref<Record<string, string[]>>({});

const rules = {
  eventIdentifier: {
    required: helpers.withMessage(
      t('transactions.events.form.event_identifier.validation.non_empty'),
      requiredIf(() => !!get(editableItem)),
    ),
  },
  timestamp: { externalServerValidation: () => true },
  amount: {
    required: helpers.withMessage(t('transactions.events.form.amount.validation.non_empty'), required),
  },
  usdValue: {
    required: helpers.withMessage(
      t('transactions.events.form.fiat_value.validation.non_empty', {
        currency: get(currencySymbol),
      }),
      required,
    ),
  },
  blockNumber: {
    required: helpers.withMessage(t('transactions.events.form.block_number.validation.non_empty'), required),
  },
  validatorIndex: {
    required: helpers.withMessage(t('transactions.events.form.validator_index.validation.non_empty'), required),
  },
  feeRecipient: {
    required: helpers.withMessage(t('transactions.events.form.fee_recipient.validation.non_empty'), required),
    isValid: helpers.withMessage(t('transactions.events.form.fee_recipient.validation.valid'), (value: string) =>
      isValidEthAddress(value)),
  },
};

const numericAmount = bigNumberifyFromRef(amount);
const numericUsdValue = bigNumberifyFromRef(usdValue);

const { setValidation, setSubmitFunc, saveHistoryEventHandler } = useHistoryEventsForm();

const v$ = setValidation(
  rules,
  {
    eventIdentifier,
    timestamp: datetime,
    amount,
    usdValue,
    blockNumber,
    validatorIndex,
    feeRecipient,
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages,
  },
);

function reset() {
  set(eventIdentifier, null);
  set(datetime, convertFromTimestamp(dayjs().valueOf(), DateFormat.DateMonthYearHourMinuteSecond, true));
  set(amount, '0');
  set(usdValue, '0');
  set(blockNumber, '');
  set(validatorIndex, '');
  set(feeRecipient, '');
  set(isMevReward, false);
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
}

function applyEditableData(entry: EthBlockEvent) {
  set(eventIdentifier, entry.eventIdentifier);
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
  set(amount, entry.balance.amount.toFixed());
  set(usdValue, entry.balance.usdValue.toFixed());
  set(blockNumber, entry.blockNumber.toString());
  set(validatorIndex, entry.validatorIndex.toString());
  set(feeRecipient, entry.locationLabel);
  set(isMevReward, entry.eventSubtype === 'mev reward');
}

function applyGroupHeaderData(entry: EthBlockEvent) {
  set(eventIdentifier, entry.eventIdentifier);
  set(feeRecipient, entry.locationLabel ?? '');
  set(blockNumber, entry.blockNumber.toString());
  set(validatorIndex, entry.validatorIndex.toString());
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
  set(usdValue, '0');
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

async function save(): Promise<boolean> {
  const timestamp = convertToTimestamp(get(datetime), DateFormat.DateMonthYearHourMinuteSecond, true);

  const payload: NewEthBlockEventPayload = {
    eventIdentifier: get(eventIdentifier),
    entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
    timestamp,
    balance: {
      amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
      usdValue: get(numericUsdValue).isNaN() ? Zero : get(numericUsdValue),
    },
    blockNumber: parseInt(get(blockNumber)),
    validatorIndex: parseInt(get(validatorIndex)),
    feeRecipient: get(feeRecipient),
    isMevReward: get(isMevReward),
  };

  const edit = get(editableItem);

  return await saveHistoryEventHandler(
    edit ? { ...payload, identifier: edit.identifier } : payload,
    assetPriceForm,
    errorMessages,
    reset,
  );
}

setSubmitFunc(save);

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

watch([groupHeader, editableItem], checkPropsData);
onMounted(() => {
  checkPropsData();
});

const { getAddresses } = useBlockchainStore();

const feeRecipientSuggestions = computed(() => getAddresses(Blockchain.ETH));
</script>

<template>
  <div>
    <div class="grid md:grid-cols-4 gap-4 mb-4">
      <DateTimePicker
        v-model="datetime"
        class="md:col-span-2"
        :label="t('common.datetime')"
        persistent-hint
        limit-now
        milliseconds
        data-cy="datetime"
        :hint="t('transactions.events.form.datetime.hint')"
        :error-messages="toMessages(v$.timestamp)"
        @blur="v$.timestamp.$touch()"
      />
      <AmountInput
        v-model="blockNumber"
        variant="outlined"
        integer
        data-cy="blockNumber"
        :label="t('transactions.events.form.block_number.label')"
        :error-messages="toMessages(v$.blockNumber)"
        @blur="v$.blockNumber.$touch()"
      />
      <AmountInput
        v-model="validatorIndex"
        variant="outlined"
        integer
        data-cy="validatorIndex"
        :label="t('transactions.events.form.validator_index.label')"
        :error-messages="toMessages(v$.validatorIndex)"
        @blur="v$.validatorIndex.$touch()"
      />
    </div>

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      ref="assetPriceForm"
      v-model:amount="amount"
      v-model:usd-value="usdValue"
      asset="ETH"
      :v$="v$"
      :datetime="datetime"
      disable-asset
    />

    <RuiDivider class="my-10" />

    <AutoCompleteWithSearchSync
      v-model="feeRecipient"
      :items="feeRecipientSuggestions"
      data-cy="feeRecipient"
      :label="t('transactions.events.form.fee_recipient.label')"
      :error-messages="toMessages(v$.feeRecipient)"
      auto-select-first
      @blur="v$.feeRecipient.$touch()"
    />

    <RuiCheckbox
      v-model="isMevReward"
      color="primary"
      data-cy="isMevReward"
    >
      {{ t('transactions.events.form.is_mev_reward.label') }}
    </RuiCheckbox>

    <RuiDivider class="mb-2 mt-6" />

    <RuiAccordions>
      <RuiAccordion
        data-cy="eth-block-event-form__advance"
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
