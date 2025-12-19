<script setup lang="ts">
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import type { EthBlockEvent, NewEthBlockEventPayload } from '@/types/history/events/schemas';
import { Blockchain, HistoryEventEntryType, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useEditModeStateTracker } from '@/composables/history/events/edit-mode-state';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { toMessages } from '@/utils/validation';

interface EthBlockEventFormProps {
  data: StandaloneEventData<EthBlockEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const props = defineProps<EthBlockEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

const { data } = toRefs(props);

const assetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('assetPriceForm');

const groupIdentifier = ref<string>('');
const timestamp = ref<number>(0);
const amount = ref<string>('');
const blockNumber = ref<string>('');
const validatorIndex = ref<string>('');
const feeRecipient = ref<string>('');
const isMevReward = ref<boolean>(false);

const errorMessages = ref<Record<string, string[]>>({});

const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const rules = {
  amount: commonRules.createRequiredAmountRule(),
  blockNumber: commonRules.createRequiredBlockNumberRule(),
  feeRecipient: commonRules.createRequiredValidFeeRecipientRule(),
  groupIdentifier: commonRules.createRequiredGroupIdentifierRule(() => get(data).type === 'edit'),
  timestamp: commonRules.createExternalValidationRule(),
  validatorIndex: commonRules.createRequiredValidatorIndexRule(),
};

const numericAmount = bigNumberifyFromRef(amount);

const { saveHistoryEventHandler } = useHistoryEventsForm();
const { captureEditModeStateFromRefs, shouldSkipSaveFromRefs } = useEditModeStateTracker();

const states = {
  amount,
  blockNumber,
  feeRecipient,
  groupIdentifier,
  isMevReward,
  timestamp,
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
  set(groupIdentifier, null);
  set(timestamp, dayjs().valueOf());
  set(amount, '0');
  set(blockNumber, '');
  set(validatorIndex, '');
  set(feeRecipient, '');
  set(isMevReward, false);
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
}

function applyEditableData(entry: EthBlockEvent) {
  set(groupIdentifier, entry.groupIdentifier);
  set(timestamp, entry.timestamp);
  set(amount, entry.amount.toFixed());
  set(blockNumber, entry.blockNumber.toString());
  set(validatorIndex, entry.validatorIndex.toString());
  set(feeRecipient, entry.locationLabel);
  set(isMevReward, entry.eventSubtype === 'mev reward');

  // Capture state snapshot for edit mode comparison
  captureEditModeStateFromRefs(states);
}

function applyGroupHeaderData(entry: EthBlockEvent) {
  set(groupIdentifier, entry.groupIdentifier);
  set(feeRecipient, entry.locationLabel ?? '');
  set(blockNumber, entry.blockNumber.toString());
  set(validatorIndex, entry.validatorIndex.toString());
  set(timestamp, entry.timestamp);
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const eventData = get(data);
  const editable = eventData.type === 'edit' ? eventData.event : undefined;

  const payload: NewEthBlockEventPayload = {
    amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
    blockNumber: parseInt(get(blockNumber)),
    entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
    feeRecipient: get(feeRecipient),
    groupIdentifier: get(groupIdentifier),
    isMevReward: get(isMevReward),
    timestamp: get(timestamp),
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

const { getAddresses } = useAccountAddresses();

const feeRecipientSuggestions = computed(() => getAddresses(Blockchain.ETH));

defineExpose({
  save,
  v$,
});
</script>

<template>
  <div>
    <div class="grid md:grid-cols-4 gap-4 mb-4">
      <DateTimePicker
        v-model="timestamp"
        class="md:col-span-2"
        :label="t('common.datetime')"
        required
        persistent-hint
        max-date="now"
        variant="outlined"
        accuracy="millisecond"
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
        required
        :error-messages="toMessages(v$.blockNumber)"
        @blur="v$.blockNumber.$touch()"
      />
      <AmountInput
        v-model="validatorIndex"
        variant="outlined"
        integer
        data-cy="validatorIndex"
        :label="t('transactions.events.form.validator_index.label')"
        required
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
      :timestamp="timestamp"
      location="ethereum"
      disable-asset
    />

    <RuiDivider class="mb-6" />

    <AutoCompleteWithSearchSync
      v-model="feeRecipient"
      :items="feeRecipientSuggestions"
      data-cy="feeRecipient"
      :label="t('transactions.events.form.fee_recipient.label')"
      required
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
            v-model="groupIdentifier"
            variant="outlined"
            color="primary"
            data-cy="groupIdentifier"
            :label="t('transactions.events.form.event_identifier.label')"
            :error-messages="toMessages(v$.groupIdentifier)"
            @blur="v$.groupIdentifier.$touch()"
          />
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>
