<script lang="ts" setup>
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import type { ValidationErrors } from '@/types/api/errors';
import type { AddEvmSwapEventPayload, EvmHistoryEvent, EvmSwapEvent } from '@/types/history/events';
import AmountInput from '@/components/inputs/AmountInput.vue';
import CounterpartyInput from '@/components/inputs/CounterpartyInput.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEvents } from '@/composables/history/events';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import EvmLocation from '@/modules/history/management/forms/common/EvmLocation.vue';
import SwapEventAssetAmount from '@/modules/history/management/forms/swap/SwapEventAssetAmount.vue';
import SwapEventFee from '@/modules/history/management/forms/swap/SwapEventFee.vue';
import SwapEventNotes from '@/modules/history/management/forms/swap/SwapEventNotes.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { useDateTime } from '@/modules/history/management/forms/utils';
import { useMessageStore } from '@/store/message';
import { toMessages } from '@/utils/validation';
import { assert, HistoryEventEntryType } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import dayjs from 'dayjs';
import { omit, pick } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';

type FormData = Required<Omit<AddEvmSwapEventPayload, 'eventIdentifier'>>;

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<{ data: StandaloneEventData<EvmHistoryEvent> | GroupEventData<EvmSwapEvent> }>();

function emptyEvent(): FormData {
  return {
    address: '',
    counterparty: '',
    entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
    feeAmount: '',
    feeAsset: '',
    location: '',
    locationLabel: '',
    receiveAmount: '',
    receiveAsset: '',
    sequenceIndex: '0',
    spendAmount: '',
    spendAsset: '',
    timestamp: dayjs().valueOf(),
    txHash: '',
    userNotes: ['', '', ''],
  };
}

const states = ref<FormData>(emptyEvent());
const hasFee = ref<boolean>(false);
const identifier = ref<number>();
const eventIdentifier = ref<string>();
const errorMessages = ref<Record<string, string[]>>({});

const datetime = useDateTime(states);

const { t } = useI18n({ useScope: 'global' });
const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const rules = {
  address: commonRules.createValidEthAddressRule(),
  counterparty: commonRules.createExternalValidationRule(),
  feeAmount: commonRules.createExternalValidationRule(),
  feeAsset: commonRules.createExternalValidationRule(),
  location: commonRules.createRequiredLocationRule(),
  locationLabel: commonRules.createExternalValidationRule(),
  receiveAmount: commonRules.createRequiredAmountRule(),
  receiveAsset: commonRules.createRequiredAssetRule(),
  sequenceIndex: commonRules.createRequiredSequenceIndexRule(),
  spendAmount: commonRules.createRequiredAmountRule(),
  spendAsset: commonRules.createRequiredAssetRule(),
  timestamp: commonRules.createExternalValidationRule(),
  txHash: commonRules.createValidTxHashRule(),
  userNotes: commonRules.createExternalValidationRule(),
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
const { setMessage } = useMessageStore();
const { addHistoryEvent, editHistoryEvent } = useHistoryEvents();

function handleValidationErrors(message: ValidationErrors | string) {
  if (typeof message === 'string') {
    setMessage({
      description: message,
    });
  }
  else {
    set(errorMessages, message);
  }
}

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const model = get(states);
  let payload: AddEvmSwapEventPayload;
  if (get(hasFee)) {
    payload = model;
  }
  else {
    payload = omit(model, ['feeAmount', 'feeAsset']);
    payload.userNotes = [model.userNotes[0], model.userNotes[1]];
  }

  if (payload.address === '') {
    payload.address = undefined;
  }

  const result = isDefined(eventIdentifier) && isDefined(identifier)
    ? await editHistoryEvent({
      ...payload,
      ...{
        eventIdentifier: get(eventIdentifier),
        identifier: get(identifier),
      },
    })
    : await addHistoryEvent(payload);

  if (result.success) {
    set(states, emptyEvent());
    set(eventIdentifier, undefined);
    set(identifier, undefined);
    set(hasFee, false);
  }
  else {
    const message = result.message;
    if (message) {
      handleValidationErrors(message);
    }
  }

  return result.success;
}

function getNotes(event?: EvmSwapEvent): string {
  if (!event || !event.userNotes) {
    return '';
  }
  return event.userNotes;
}

watchImmediate(() => props.data, (data) => {
  if (data.type === 'group-add') {
    const group = data.group;

    set(states, {
      ...get(states),
      location: group.location ?? '',
      sequenceIndex: data.nextSequenceId.toString(),
      timestamp: group.timestamp,
      txHash: group.txHash,
    });
  }
  else if (data.type === 'edit-group') {
    const spend = data.eventsInGroup.find(item => item.eventSubtype === 'spend');
    const receive = data.eventsInGroup.find(item => item.eventSubtype === 'receive');
    const fee = data.eventsInGroup.find(item => item.eventSubtype === 'fee');

    assert(spend);
    assert(receive);

    set(hasFee, fee !== undefined);
    const identifiers = pick(spend, ['eventIdentifier', 'identifier']);
    set(eventIdentifier, identifiers.eventIdentifier);
    set(identifier, identifiers.identifier);

    const userNotes: [string, string, string] | [string, string] = fee !== undefined
      ? [
          getNotes(spend),
          getNotes(receive),
          getNotes(fee),
        ]
      : [
          getNotes(spend),
          getNotes(receive),
        ];

    set(states, {
      address: spend.address ?? '',
      counterparty: spend.counterparty ?? '',
      entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
      feeAmount: fee?.amount?.toString() ?? '',
      feeAsset: fee?.asset ?? '',
      location: spend.location,
      locationLabel: spend.locationLabel ?? '',
      receiveAmount: receive.amount.toString(),
      receiveAsset: receive.asset,
      sequenceIndex: spend.sequenceIndex.toString(),
      spendAmount: spend.amount.toString(),
      spendAsset: spend.asset,
      timestamp: spend.timestamp,
      txHash: spend.txHash,
      userNotes,
    });
  }
});

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

defineExpose({
  save,
});
</script>

<template>
  <div>
    <EventDateLocation
      v-model:datetime="datetime"
      v-model:location="states.location"
      location-disabled
      :error-messages="{
        location: toMessages(v$.location),
        datetime: toMessages(v$.timestamp),
      }"
      @blur="v$[$event].$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextField
      v-model="states.txHash"
      variant="outlined"
      color="primary"
      disabled
      data-cy="tx-hash"
      :label="t('common.tx_hash')"
      :error-messages="toMessages(v$.txHash)"
      @blur="v$.txHash.$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <SwapEventAssetAmount
      v-model:asset="states.spendAsset"
      v-model:amount="states.spendAmount"
      type="spend"
      :error-messages="{
        asset: toMessages(v$.spendAsset),
        amount: toMessages(v$.spendAmount),
      }"
    />

    <SwapEventAssetAmount
      v-model:asset="states.receiveAsset"
      v-model:amount="states.receiveAmount"
      type="receive"
      :error-messages="{
        asset: toMessages(v$.receiveAsset),
        amount: toMessages(v$.receiveAmount),
      }"
    />

    <RuiDivider class="mb-6 mt-2" />

    <SwapEventFee
      v-model="hasFee"
      v-model:amount="states.feeAmount"
      v-model:asset="states.feeAsset"
      :error-messages="{
        fee: toMessages(v$.feeAmount),
        amount: toMessages(v$.feeAsset),
      }"
    />

    <RuiDivider class="mb-6 mt-2" />

    <EvmLocation
      v-model:location-label="states.locationLabel"
      v-model:address="states.address"
      :error-messages="{
        locationLabel: toMessages(v$.locationLabel),
        address: toMessages(v$.address),
      }"
      @blur="v$[$event].$touch()"
    />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="states.sequenceIndex"
        variant="outlined"
        integer
        :disabled="data.type === 'edit-group'"
        data-cy="sequence-index"
        :label="t('transactions.events.form.sequence_index.label')"
        :error-messages="toMessages(v$.sequenceIndex)"
        @blur="v$.sequenceIndex.$touch()"
      />

      <CounterpartyInput
        v-model="states.counterparty"
        :label="t('common.counterparty')"
        data-cy="counterparty"
        :error-messages="toMessages(v$.counterparty)"
        @blur="v$.counterparty.$touch()"
      />
    </div>

    <SwapEventNotes
      v-model="states.userNotes"
      :has-fee="hasFee"
      :error-messages="toMessages(v$.userNotes)"
      @blur="v$.userNotes.$touch()"
    />
  </div>
</template>
