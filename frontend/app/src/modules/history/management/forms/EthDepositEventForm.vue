<script setup lang="ts">
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import type { EthDepositEvent, NewEthDepositEventPayload } from '@/types/history/events/schemas';
import { Blockchain, HistoryEventEntryType, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import JsonInput from '@/components/inputs/JsonInput.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useEditModeStateTracker } from '@/composables/history/events/edit-mode-state';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { toMessages } from '@/utils/validation';

interface EthDepositEventFormProps {
  data: StandaloneEventData<EthDepositEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const props = defineProps<EthDepositEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

const { data } = toRefs(props);

const assetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('assetPriceForm');

const txRef = ref<string>('');
const eventIdentifier = ref<string>('');
const timestamp = ref<number>(0);
const amount = ref<string>('');
const sequenceIndex = ref<string>('');
const validatorIndex = ref<string>('');
const depositor = ref<string>('');
const extraData = ref<object>({});

const errorMessages = ref<Record<string, string[]>>({});

const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const rules = {
  amount: commonRules.createRequiredAmountRule(),
  depositor: commonRules.createRequiredValidDepositorRule(),
  eventIdentifier: commonRules.createRequiredEventIdentifierRule(() => get(data).type === 'edit'),
  sequenceIndex: commonRules.createRequiredSequenceIndexRule(),
  timestamp: commonRules.createExternalValidationRule(),
  txRef: commonRules.createValidTxHashRule(),
  validatorIndex: commonRules.createRequiredValidatorIndexRule(),
};

const numericAmount = bigNumberifyFromRef(amount);

const { saveHistoryEventHandler } = useHistoryEventsForm();
const { getAddresses } = useAccountAddresses();
const { captureEditModeStateFromRefs, shouldSkipSaveFromRefs } = useEditModeStateTracker();

const states = {
  amount,
  depositor,
  eventIdentifier,
  extraData,
  sequenceIndex,
  timestamp,
  txRef,
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
  set(sequenceIndex, get(data)?.nextSequenceId || '0');
  set(txRef, '');
  set(eventIdentifier, null);
  set(timestamp, dayjs().valueOf());
  set(amount, '0');
  set(validatorIndex, '');
  set(depositor, '');
  set(extraData, {});
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
}

function applyEditableData(entry: EthDepositEvent) {
  set(sequenceIndex, entry.sequenceIndex?.toString() ?? '');
  set(txRef, entry.txRef);
  set(eventIdentifier, entry.eventIdentifier);
  set(timestamp, entry.timestamp);
  set(amount, entry.amount.toFixed());
  set(validatorIndex, entry.validatorIndex.toString());
  set(depositor, entry.locationLabel);
  set(extraData, entry.extraData || {});

  // Capture state snapshot for edit mode comparison
  captureEditModeStateFromRefs(states);
}

function applyGroupHeaderData(entry: EthDepositEvent) {
  set(sequenceIndex, get(data)?.nextSequenceId || '0');
  set(eventIdentifier, entry.eventIdentifier);
  set(txRef, entry.txRef);
  set(validatorIndex, entry.validatorIndex.toString());
  set(depositor, entry.locationLabel ?? '');
  set(timestamp, entry.timestamp);
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate()))
    return false;

  const eventData = get(data);
  const editable = eventData.type === 'edit' ? eventData.event : undefined;

  const payload: NewEthDepositEventPayload = {
    amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
    depositor: get(depositor),
    entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
    eventIdentifier: get(eventIdentifier) ?? null,
    extraData: get(extraData) || null,
    sequenceIndex: get(sequenceIndex) || '0',
    timestamp: get(timestamp),
    txRef: get(txRef),
    validatorIndex: parseInt(get(validatorIndex)),
  };

  return await saveHistoryEventHandler(
    editable ? { ...payload, identifier: editable.identifier } : payload,
    assetPriceForm,
    errorMessages,
    reset,
    shouldSkipSaveFromRefs(!!editable, states),
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
      <RuiDateTimePicker
        v-model="timestamp"
        :label="t('common.datetime')"
        persistent-hint
        max-date="now"
        color="primary"
        variant="outlined"
        accuracy="millisecond"
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
      v-model="txRef"
      variant="outlined"
      color="primary"
      data-cy="tx-ref"
      :label="t('common.tx_hash')"
      :error-messages="toMessages(v$.txRef)"
      @blur="v$.txRef.$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      ref="assetPriceForm"
      v-model:amount="amount"
      asset="ETH"
      :v$="v$"
      :timestamp="timestamp"
      location="ethereum"
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
        data-cy="sequence-index"
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
