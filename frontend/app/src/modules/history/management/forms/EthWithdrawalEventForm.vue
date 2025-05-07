<script setup lang="ts">
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import type { EthWithdrawalEvent, NewEthWithdrawalEventPayload } from '@/types/history/events';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { DateFormat } from '@/types/date-format';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { toMessages } from '@/utils/validation';
import { Blockchain, HistoryEventEntryType, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';

interface EthWithdrawalEventFormProps {
  data: StandaloneEventData<EthWithdrawalEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<EthWithdrawalEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

const { data } = toRefs(props);

const assetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('assetPriceForm');

const eventIdentifier = ref<string>('');
const datetime = ref<string>('');
const amount = ref<string>('');
const validatorIndex = ref<string>('');
const withdrawalAddress = ref<string>('');
const isExit = ref<boolean>(false);

const errorMessages = ref<Record<string, string[]>>({});

const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const rules = {
  amount: commonRules.createRequiredAmountRule(),
  eventIdentifier: commonRules.createRequiredEventIdentifierRule(() => get(data).type === 'edit'),
  timestamp: commonRules.createExternalValidationRule(),
  validatorIndex: commonRules.createRequiredValidatorIndexRule(),
  withdrawalAddress: commonRules.createRequiredValidWithdrawalAddressRule(),
};

const numericAmount = bigNumberifyFromRef(amount);

const { saveHistoryEventHandler } = useHistoryEventsForm();
const { getAddresses } = useAccountAddresses();

const states = {
  amount,
  eventIdentifier,
  timestamp: datetime,
  validatorIndex,
  withdrawalAddress,
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

const withdrawalAddressSuggestions = computed(() => getAddresses(Blockchain.ETH));

function reset() {
  set(eventIdentifier, null);
  set(datetime, convertFromTimestamp(dayjs().valueOf(), DateFormat.DateMonthYearHourMinuteSecond, true));
  set(amount, '0');
  set(validatorIndex, '');
  set(withdrawalAddress, '');
  set(isExit, false);
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
}

function applyEditableData(entry: EthWithdrawalEvent) {
  set(eventIdentifier, entry.eventIdentifier);
  set(datetime, convertFromTimestamp(entry.timestamp, DateFormat.DateMonthYearHourMinuteSecond, true));
  set(amount, entry.amount.toFixed());
  set(validatorIndex, entry.validatorIndex.toString());
  set(withdrawalAddress, entry.locationLabel);
  set(isExit, entry.isExit);
}

function applyGroupHeaderData(entry: EthWithdrawalEvent) {
  set(eventIdentifier, entry.eventIdentifier);
  set(withdrawalAddress, entry.locationLabel ?? '');
  set(validatorIndex, entry.validatorIndex.toString());
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

  const payload: NewEthWithdrawalEventPayload = {
    amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
    entryType: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT,
    eventIdentifier: get(eventIdentifier),
    isExit: get(isExit),
    timestamp,
    validatorIndex: parseInt(get(validatorIndex)),
    withdrawalAddress: get(withdrawalAddress),
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
      v-model="withdrawalAddress"
      :items="withdrawalAddressSuggestions"
      data-cy="withdrawalAddress"
      :label="t('transactions.events.form.withdrawal_address.label')"
      :error-messages="toMessages(v$.withdrawalAddress)"
      auto-select-first
      @blur="v$.withdrawalAddress.$touch()"
    />

    <RuiCheckbox
      v-model="isExit"
      color="primary"
      data-cy="is-exit"
    >
      {{ t('transactions.events.form.is_exit.label') }}
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
