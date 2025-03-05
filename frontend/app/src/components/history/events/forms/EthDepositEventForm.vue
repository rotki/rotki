<script setup lang="ts">
import { Blockchain, HistoryEventEntryType } from '@rotki/common';
import dayjs from 'dayjs';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { isEmpty } from 'es-toolkit/compat';
import useVuelidate from '@vuelidate/core';
import { toMessages } from '@/utils/validation';
import { DateFormat } from '@/types/date-format';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';
import { useBlockchainStore } from '@/store/blockchain';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import JsonInput from '@/components/inputs/JsonInput.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import type { EthDepositEvent, NewEthDepositEventPayload } from '@/types/history/events';

interface EthDepositEventFormProps {
  editableItem?: EthDepositEvent;
  nextSequence?: string;
  groupHeader?: EthDepositEvent;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const props = withDefaults(defineProps<EthDepositEventFormProps>(), {
  editableItem: undefined,
  groupHeader: undefined,
  nextSequence: '',
});

const { t } = useI18n();

const { editableItem, groupHeader, nextSequence } = toRefs(props);

const assetPriceForm = ref<InstanceType<typeof HistoryEventAssetPriceForm>>();

const txHash = ref<string>('');
const eventIdentifier = ref<string>('');
const datetime = ref<string>('');
const amount = ref<string>('');
const sequenceIndex = ref<string>('');
const validatorIndex = ref<string>('');
const depositor = ref<string>('');
const extraData = ref<object>({});

const errorMessages = ref<Record<string, string[]>>({});

const rules = {
  amount: {
    required: helpers.withMessage(t('transactions.events.form.amount.validation.non_empty'), required),
  },
  depositor: {
    isValid: helpers.withMessage(t('transactions.events.form.depositor.validation.valid'), (value: string) =>
      isValidEthAddress(value)),
    required: helpers.withMessage(t('transactions.events.form.depositor.validation.non_empty'), required),
  },
  eventIdentifier: {
    required: helpers.withMessage(
      t('transactions.events.form.event_identifier.validation.non_empty'),
      requiredIf(() => !!get(editableItem)),
    ),
  },
  sequenceIndex: {
    required: helpers.withMessage(t('transactions.events.form.sequence_index.validation.non_empty'), required),
  },
  timestamp: { externalServerValidation: () => true },
  txHash: {
    isValid: helpers.withMessage(t('transactions.events.form.tx_hash.validation.valid'), (value: string) =>
      isValidTxHash(value)),
    required: helpers.withMessage(t('transactions.events.form.tx_hash.validation.non_empty'), required),
  },
  validatorIndex: {
    required: helpers.withMessage(t('transactions.events.form.validator_index.validation.non_empty'), required),
  },
};

const numericAmount = bigNumberifyFromRef(amount);

const { saveHistoryEventHandler } = useHistoryEventsForm();
const { getAddresses } = useBlockchainStore();

const states = {
  amount,
  depositor,
  eventIdentifier,
  sequenceIndex,
  timestamp: datetime,
  txHash,
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

const depositorSuggestions = computed(() => getAddresses(Blockchain.ETH));

function reset() {
  set(sequenceIndex, get(nextSequence) || '0');
  set(txHash, '');
  set(eventIdentifier, null);
  set(datetime, convertFromTimestamp(dayjs().valueOf(), DateFormat.DateMonthYearHourMinuteSecond, true));
  set(amount, '0');
  set(validatorIndex, '');
  set(depositor, '');
  set(extraData, {});
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
}

function applyEditableData(entry: EthDepositEvent) {
  set(sequenceIndex, entry.sequenceIndex?.toString() ?? '');
  set(txHash, entry.txHash);
  set(eventIdentifier, entry.eventIdentifier);
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
  set(amount, entry.amount.toFixed());
  set(validatorIndex, entry.validatorIndex.toString());
  set(depositor, entry.locationLabel);
  set(extraData, entry.extraData || {});
}

function applyGroupHeaderData(entry: EthDepositEvent) {
  set(sequenceIndex, get(nextSequence) || '0');
  set(eventIdentifier, entry.eventIdentifier);
  set(txHash, entry.txHash);
  set(validatorIndex, entry.validatorIndex.toString());
  set(depositor, entry.locationLabel ?? '');
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate()))
    return false;

  const timestamp = convertToTimestamp(get(datetime), DateFormat.DateMonthYearHourMinuteSecond, true);

  const payload: NewEthDepositEventPayload = {
    amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
    depositor: get(depositor),
    entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
    eventIdentifier: get(eventIdentifier) ?? null,
    extraData: get(extraData) || null,
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp,
    txHash: get(txHash),
    validatorIndex: parseInt(get(validatorIndex)),
  };

  const edit = get(editableItem);

  return await saveHistoryEventHandler(
    edit ? { ...payload, identifier: edit.identifier } : payload,
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

watch([groupHeader, editableItem], checkPropsData);

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

    <RuiTextField
      v-model="txHash"
      variant="outlined"
      color="primary"
      data-cy="txHash"
      :label="t('common.tx_hash')"
      :error-messages="toMessages(v$.txHash)"
      @blur="v$.txHash.$touch()"
    />

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

    <div class="grid md:grid-cols-2 gap-4">
      <AutoCompleteWithSearchSync
        v-model="depositor"
        :items="depositorSuggestions"
        data-cy="depositor"
        :label="t('transactions.events.form.depositor.label')"
        :error-messages="toMessages(v$.depositor)"
        auto-select-first
        @blur="v$.depositor.$touch()"
      />

      <AmountInput
        v-model="sequenceIndex"
        variant="outlined"
        integer
        data-cy="sequenceIndex"
        :label="t('transactions.events.form.sequence_index.label')"
        :error-messages="toMessages(v$.sequenceIndex)"
        @blur="v$.sequenceIndex.$touch()"
      />
    </div>

    <RuiDivider class="mb-2 mt-6" />

    <RuiAccordions>
      <RuiAccordion
        data-cy="eth-deposit-event-form__advance"
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
