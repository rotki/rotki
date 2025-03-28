<script setup lang="ts">
import type { IndependentEventData } from '@/modules/history/management/forms/form-types';
import type { EthBlockEvent, NewEthBlockEventPayload } from '@/types/history/events';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { DateFormat } from '@/types/date-format';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { toMessages } from '@/utils/validation';
import { Blockchain, HistoryEventEntryType, isValidEthAddress, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';

interface EthBlockEventFormProps {
  data: IndependentEventData<EthBlockEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const props = defineProps<EthBlockEventFormProps>();

const { t } = useI18n();

const { data } = toRefs(props);

const assetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('assetPriceForm');

const eventIdentifier = ref<string>('');
const datetime = ref<string>('');
const amount = ref<string>('');
const blockNumber = ref<string>('');
const validatorIndex = ref<string>('');
const feeRecipient = ref<string>('');
const isMevReward = ref<boolean>(false);

const errorMessages = ref<Record<string, string[]>>({});

const rules = {
  amount: {
    required: helpers.withMessage(t('transactions.events.form.amount.validation.non_empty'), required),
  },
  blockNumber: {
    required: helpers.withMessage(t('transactions.events.form.block_number.validation.non_empty'), required),
  },
  eventIdentifier: {
    required: helpers.withMessage(
      t('transactions.events.form.event_identifier.validation.non_empty'),
      requiredIf(() => get(data).type === 'edit'),
    ),
  },
  feeRecipient: {
    isValid: helpers.withMessage(t('transactions.events.form.fee_recipient.validation.valid'), (value: string) =>
      isValidEthAddress(value)),
    required: helpers.withMessage(t('transactions.events.form.fee_recipient.validation.non_empty'), required),
  },
  timestamp: { externalServerValidation: () => true },
  validatorIndex: {
    required: helpers.withMessage(t('transactions.events.form.validator_index.validation.non_empty'), required),
  },
};

const numericAmount = bigNumberifyFromRef(amount);

const { saveHistoryEventHandler } = useHistoryEventsForm();

const states = {
  amount,
  blockNumber,
  eventIdentifier,
  feeRecipient,
  timestamp: datetime,
  validatorIndex,
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
  set(eventIdentifier, null);
  set(datetime, convertFromTimestamp(dayjs().valueOf(), DateFormat.DateMonthYearHourMinuteSecond, true));
  set(amount, '0');
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
  set(amount, entry.amount.toFixed());
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

  const payload: NewEthBlockEventPayload = {
    amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
    blockNumber: parseInt(get(blockNumber)),
    entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
    eventIdentifier: get(eventIdentifier),
    feeRecipient: get(feeRecipient),
    isMevReward: get(isMevReward),
    timestamp,
    validatorIndex: parseInt(get(validatorIndex)),
  };

  const eventData = get(data);
  const edit = eventData.type === 'edit' ? eventData.event : undefined;

  return await saveHistoryEventHandler(
    edit ? { ...payload, identifier: edit.identifier } : payload,
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

watch(data, checkPropsData);
onMounted(() => {
  checkPropsData();
});

const { getAddresses } = useAccountAddresses();

const feeRecipientSuggestions = computed(() => getAddresses(Blockchain.ETH));

defineExpose({
  save,
});
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
      asset="ETH"
      :v$="v$"
      :datetime="datetime"
      disable-asset
    />

    <RuiDivider class="mb-6" />

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

    <RuiDivider class="mb-2" />

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
